import io
import json
import os
import socket
import sqlite3
from typing import Optional
import qrcode
import qrcode.image.svg
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="ระบบลงคะแนนการแข่งขันวงดนตรี")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(__file__), "scoring.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# Pydantic Models
class LoginRequest(BaseModel):
    phone: str
    pin: str


class QrCheckinRequest(BaseModel):
    category_id: str
    judge_id: int
    phone: str
    email: str


class UpdatePinRequest(BaseModel):
    judge_id: int
    old_pin: str
    new_pin: str


class AdminUpdateJudgeRequest(BaseModel):
    admin_id: int
    judge_id: int
    phone: Optional[str] = None
    email: Optional[str] = None
    pin: Optional[str] = None
    reset_verification: Optional[bool] = False


class ScoreSubmitRequest(BaseModel):
    judge_id: int
    competitor_id: int
    art_1: float
    art_2: float
    art_3: float
    art_4: float
    ens_1: float
    ens_2: float
    ens_3: float
    tech_1: float
    tech_2: float
    tech_3: float
    comments: Optional[str] = ""
    edit_reason: Optional[str] = ""
    edited_fields: Optional[str] = ""


class EditRequestCreate(BaseModel):
    judge_id: int
    competitor_id: int
    reason: str
    target_fields: Optional[str] = ""


class EditRequestReview(BaseModel):
    admin_id: int
    action: str  # 'approve' or 'reject'
    admin_note: Optional[str] = ""


class AddCompetitorRequest(BaseModel):
    admin_id: int
    category_id: str
    order_no: Optional[int] = None
    school_name: str
    affiliation_group: Optional[str] = "-"
    students_info: Optional[str] = ""
    teachers_info: Optional[str] = ""


class DeleteCompetitorRequest(BaseModel):
    admin_id: int
    competitor_id: int


def get_medal(score: float) -> str:
    if score >= 80:
        return "เหรียญทอง"
    elif score >= 70:
        return "เหรียญเงิน"
    elif score >= 60:
        return "เหรียญทองแดง"
    return "เกียรติบัตรเข้าร่วม"


def get_lan_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        primary = s.getsockname()[0]
        s.close()
        if primary and not primary.startswith("127."):
            if primary in ips:
                ips.remove(primary)
            ips.insert(0, primary)
    except Exception:
        pass
    return ips


# --- Utility / QR Endpoints ---
@app.get("/api/server-info")
def server_info():
    return {
        "ips": get_lan_ips(),
        "port": 8000,
    }


@app.get("/api/qr")
def generate_qr(url: str = Query(..., min_length=1)):
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return Response(content=buf.getvalue(), media_type="image/svg+xml")


# --- Judge & Auth Endpoints ---
@app.get("/api/judges")
def get_all_judges(conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT id, phone, email, fullname, position, school, is_admin, is_verified FROM judges ORDER BY id ASC")
    return [dict(row) for row in cursor.fetchall()]


@app.post("/api/judges/login")
def login_chairman(req: LoginRequest, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, phone, email, pin, fullname, position, school, is_admin FROM judges WHERE phone = ?",
        (req.phone.strip(),),
    )
    judge = cursor.fetchone()
    if not judge or not judge["is_admin"]:
        raise HTTPException(
            status_code=403,
            detail="เฉพาะประธานกรรมการเท่านั้นที่เข้าสู่ระบบหน้านี้ กรรมการท่านอื่นกรุณาสแกน QR Code จากประธานกรรมการ",
        )
    if judge["pin"] and judge["pin"] != req.pin.strip():
        raise HTTPException(status_code=401, detail="รหัส PIN ไม่ถูกต้อง")

    return {
        "success": True,
        "judge": {
            "id": judge["id"],
            "phone": judge["phone"],
            "email": judge["email"] or "",
            "fullname": judge["fullname"],
            "position": judge["position"],
            "school": judge["school"],
            "is_admin": True,
        },
    }


@app.post("/api/judges/qr-checkin")
def qr_checkin_judge(req: QrCheckinRequest, conn: sqlite3.Connection = Depends(get_db)):
    phone = req.phone.strip()
    email = req.email.strip()

    if not phone or len(phone) < 9:
        raise HTTPException(status_code=400, detail="กรุณากรอกเบอร์โทรศัพท์ให้ถูกต้อง (อย่างน้อย 9 หลัก)")
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="กรุณากรอกอีเมลให้ถูกต้อง")

    cursor = conn.cursor()
    cursor.execute("""
    SELECT cj.role, j.*
    FROM category_judges cj
    JOIN judges j ON cj.judge_id = j.id
    WHERE cj.category_id = ? AND j.id = ?
    """, (req.category_id, req.judge_id))
    judge = cursor.fetchone()

    if not judge:
        raise HTTPException(status_code=404, detail="ไม่พบรายชื่อกรรมการท่านนี้ในรายการแข่งขันที่เลือก")

    if judge["is_admin"]:
        if phone != (judge["phone"] or ""):
            raise HTTPException(status_code=403, detail="เบอร์โทรศัพท์ของประธานกรรมการไม่ถูกต้อง")
        if email and not judge["email"]:
            cursor.execute("UPDATE judges SET email = ? WHERE id = ?", (email, judge["id"]))
            conn.commit()
    else:
        if judge["is_verified"] == 0:
            # First time check-in: check phone uniqueness
            cursor.execute("SELECT id FROM judges WHERE phone = ? AND id != ?", (phone, judge["id"]))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="เบอร์โทรศัพท์นี้ถูกใช้งานโดยกรรมการท่านอื่นแล้ว")

            cursor.execute("""
            UPDATE judges SET phone = ?, email = ?, is_verified = 1
            WHERE id = ?
            """, (phone, email, judge["id"]))
            conn.commit()
        else:
            # Returning check-in: verify matching phone & email
            saved_phone = (judge["phone"] or "").strip()
            saved_email = (judge["email"] or "").strip().lower()
            if phone != saved_phone or email.lower() != saved_email:
                raise HTTPException(
                    status_code=403,
                    detail="รายชื่อกรรมการนี้ได้ลงทะเบียนยืนยันตัวตนแล้ว ข้อมูลเบอร์โทรหรืออีเมลไม่ตรงกัน (หากพิมพ์ผิดกรุณาแจ้งประธานกรรมการเพื่อรีเซ็ต)",
                )

    return {
        "success": True,
        "judge": {
            "id": judge["id"],
            "phone": phone,
            "email": email,
            "fullname": judge["fullname"],
            "position": judge["position"],
            "school": judge["school"],
            "is_admin": bool(judge["is_admin"]),
            "role": judge["role"],
        },
    }


@app.post("/api/judges/update-pin")
def update_pin(req: UpdatePinRequest, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT pin, is_admin FROM judges WHERE id = ?", (req.judge_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลกรรมการ")
    if row["pin"] and row["pin"] != req.old_pin.strip():
        raise HTTPException(status_code=400, detail="รหัส PIN เดิมไม่ถูกต้อง")

    cursor.execute("UPDATE judges SET pin = ? WHERE id = ?", (req.new_pin.strip(), req.judge_id))
    conn.commit()
    return {"success": True, "message": "เปลี่ยนรหัส PIN สำเร็จ"}


@app.post("/api/admin/update-judge")
def admin_update_judge(req: AdminUpdateJudgeRequest, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM judges WHERE id = ?", (req.admin_id,))
    admin = cursor.fetchone()
    if not admin or not admin["is_admin"]:
        raise HTTPException(status_code=403, detail="เฉพาะประธานกรรมการ / แอดมินเท่านั้น")

    if req.reset_verification:
        cursor.execute(
            "UPDATE judges SET phone = NULL, email = '', is_verified = 0 WHERE id = ? AND is_admin = 0",
            (req.judge_id,),
        )
        conn.commit()
        return {"success": True, "message": "รีเซ็ตการยืนยันตัวตนของกรรมการเรียบร้อยแล้ว กรรมการสามารถสแกน QR กรอกเบอร์โทรและอีเมลใหม่ได้"}

    phone_val = req.phone.strip() if req.phone and req.phone.strip() else None
    email_val = req.email.strip() if req.email else ""

    if req.pin and req.pin.strip():
        cursor.execute(
            "UPDATE judges SET phone = ?, email = ?, pin = ? WHERE id = ?",
            (phone_val, email_val, req.pin.strip(), req.judge_id),
        )
    else:
        cursor.execute(
            "UPDATE judges SET phone = ?, email = ? WHERE id = ?",
            (phone_val, email_val, req.judge_id),
        )
    conn.commit()
    return {"success": True, "message": "อัปเดตข้อมูลกรรมการเรียบร้อยแล้ว"}


@app.post("/api/admin/competitors/add")
def admin_add_competitor(req: AddCompetitorRequest, conn: sqlite3.Connection = Depends(get_db)):
    school_name = req.school_name.strip()
    if not school_name:
        raise HTTPException(status_code=400, detail="กรุณากรอกชื่อโรงเรียน หรือชื่อวงดนตรี")

    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM judges WHERE id = ?", (req.admin_id,))
    admin = cursor.fetchone()
    if not admin or not admin["is_admin"]:
        raise HTTPException(status_code=403, detail="เฉพาะประธานกรรมการ / แอดมินเท่านั้นที่สามารถเพิ่มวงหรือโรงเรียนได้")

    cursor.execute("SELECT id FROM categories WHERE id = ?", (req.category_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="ไม่พบรายการแข่งขันที่เลือก")

    order_no = req.order_no
    if not order_no or order_no <= 0:
        cursor.execute("SELECT COALESCE(MAX(order_no), 0) FROM competitors WHERE category_id = ?", (req.category_id,))
        order_no = cursor.fetchone()[0] + 1

    affiliation = (req.affiliation_group or "-").strip() or "-"
    cursor.execute("""
    INSERT INTO competitors (category_id, order_no, school_name, affiliation_group, students_info, teachers_info)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (req.category_id, order_no, school_name, affiliation, (req.students_info or "").strip(), (req.teachers_info or "").strip()))
    conn.commit()
    new_id = cursor.lastrowid
    return {
        "success": True,
        "message": "เพิ่มวง / โรงเรียนเข้าแข่งขันเรียบร้อยแล้ว",
        "competitor": {
            "id": new_id,
            "category_id": req.category_id,
            "order_no": order_no,
            "school_name": school_name,
            "affiliation_group": affiliation,
        },
    }


@app.post("/api/admin/competitors/delete")
def admin_delete_competitor(req: DeleteCompetitorRequest, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM judges WHERE id = ?", (req.admin_id,))
    admin = cursor.fetchone()
    if not admin or not admin["is_admin"]:
        raise HTTPException(status_code=403, detail="เฉพาะประธานกรรมการ / แอดมินเท่านั้น")

    cursor.execute("SELECT COUNT(*) FROM scores WHERE competitor_id = ?", (req.competitor_id,))
    if cursor.fetchone()[0] > 0:
        raise HTTPException(status_code=400, detail="ไม่สามารถลบโรงเรียนที่มีกรรมการลงคะแนนแล้วได้")

    cursor.execute("DELETE FROM competitors WHERE id = ?", (req.competitor_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลโรงเรียนที่ต้องการลบ")
    conn.commit()
    return {"success": True, "message": "ลบรายชื่อโรงเรียนเรียบร้อยแล้ว"}


# --- Categories & Competitors ---
@app.get("/api/categories")
def get_categories(judge_id: Optional[int] = None, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories ORDER BY id ASC")
    cats = [dict(row) for row in cursor.fetchall()]

    for cat in cats:
        cursor.execute("SELECT COUNT(*) FROM competitors WHERE category_id = ?", (cat["id"],))
        cat["total_competitors"] = cursor.fetchone()[0]

        cursor.execute("""
        SELECT j.id, j.fullname, j.school, j.position, j.is_verified, j.is_admin, cj.role, cj.order_no
        FROM category_judges cj
        JOIN judges j ON cj.judge_id = j.id
        WHERE cj.category_id = ?
        ORDER BY cj.order_no ASC
        """, (cat["id"],))
        cat["judges"] = [dict(r) for r in cursor.fetchall()]

        if judge_id:
            cursor.execute(
                "SELECT role FROM category_judges WHERE category_id = ? AND judge_id = ?",
                (cat["id"], judge_id),
            )
            assigned = cursor.fetchone()
            cat["is_assigned"] = assigned is not None
            cat["judge_role"] = assigned["role"] if assigned else None

            cursor.execute("""
            SELECT COUNT(*) FROM scores s
            JOIN competitors c ON s.competitor_id = c.id
            WHERE s.judge_id = ? AND c.category_id = ?
            """, (judge_id, cat["id"]))
            cat["scored_competitors"] = cursor.fetchone()[0]
        else:
            cat["is_assigned"] = True
            cat["judge_role"] = None
            cat["scored_competitors"] = 0

    return cats


@app.get("/api/categories/{category_id}/info")
def get_single_category_info(category_id: str, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
    cat = cursor.fetchone()
    if not cat:
        raise HTTPException(status_code=404, detail="ไม่พบรายการแข่งขันนี้")
    cat_dict = dict(cat)

    cursor.execute("SELECT COUNT(*) FROM competitors WHERE category_id = ?", (category_id,))
    cat_dict["total_competitors"] = cursor.fetchone()[0]

    cursor.execute("""
    SELECT j.id, j.fullname, j.school, j.position, j.is_verified, j.is_admin, cj.role, cj.order_no
    FROM category_judges cj
    JOIN judges j ON cj.judge_id = j.id
    WHERE cj.category_id = ?
    ORDER BY cj.order_no ASC
    """, (category_id,))
    cat_dict["judges"] = [dict(r) for r in cursor.fetchall()]
    return cat_dict


@app.get("/api/categories/{category_id}/competitors")
def get_category_competitors(category_id: str, judge_id: Optional[int] = None, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("""
    SELECT c.*,
           s.id AS score_id,
           s.art_1, s.art_2, s.art_3, s.art_4,
           s.ens_1, s.ens_2, s.ens_3,
           s.tech_1, s.tech_2, s.tech_3,
           s.artistic_score, s.ensemble_score, s.technique_score, s.total_score,
           s.comments, s.is_locked, s.submitted_at, s.updated_at
    FROM competitors c
    LEFT JOIN scores s ON c.id = s.competitor_id AND s.judge_id = ?
    WHERE c.category_id = ?
    ORDER BY c.order_no ASC
    """, (judge_id, category_id))

    rows = cursor.fetchall()
    competitors = []
    for r in rows:
        d = dict(r)
        d["is_scored"] = d["total_score"] is not None

        if judge_id:
            cursor.execute("""
            SELECT id, reason, target_fields, status, admin_note, created_at, reviewed_at
            FROM edit_requests
            WHERE judge_id = ? AND competitor_id = ?
            ORDER BY id DESC LIMIT 1
            """, (judge_id, d["id"]))
            req_row = cursor.fetchone()
            d["latest_edit_request"] = dict(req_row) if req_row else None

            cursor.execute("""
            SELECT id, old_total, new_total, reason, edited_fields, edited_at
            FROM score_edit_logs
            WHERE judge_id = ? AND competitor_id = ?
            ORDER BY id DESC
            """, (judge_id, d["id"]))
            d["edit_logs"] = [dict(l) for l in cursor.fetchall()]
        else:
            d["latest_edit_request"] = None
            d["edit_logs"] = []

        competitors.append(d)
    return competitors


# --- Scoring & Edit Approval ---
@app.post("/api/scores/submit")
def submit_score(req: ScoreSubmitRequest, conn: sqlite3.Connection = Depends(get_db)):
    sub_fields = [
        ("art_1", req.art_1), ("art_2", req.art_2), ("art_3", req.art_3), ("art_4", req.art_4),
        ("ens_1", req.ens_1), ("ens_2", req.ens_2), ("ens_3", req.ens_3),
        ("tech_1", req.tech_1), ("tech_2", req.tech_2), ("tech_3", req.tech_3),
    ]
    for name, val in sub_fields:
        if not (0 <= val <= 10):
            raise HTTPException(status_code=400, detail=f"คะแนนหัวข้อย่อย ({name}) ต้องอยู่ระหว่าง 0 - 10 คะแนน")

    artistic_score = round(req.art_1 + req.art_2 + req.art_3 + req.art_4, 2)
    ensemble_score = round(req.ens_1 + req.ens_2 + req.ens_3, 2)
    technique_score = round(req.tech_1 + req.tech_2 + req.tech_3, 2)
    total_score = round(artistic_score + ensemble_score + technique_score, 2)

    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM judges WHERE id = ?", (req.judge_id,))
    judge_row = cursor.fetchone()
    if not judge_row:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลกรรมการ")
    is_admin = bool(judge_row["is_admin"])

    cursor.execute("SELECT * FROM scores WHERE judge_id = ? AND competitor_id = ?", (req.judge_id, req.competitor_id))
    existing = cursor.fetchone()

    if existing:
        if existing["is_locked"] == 1 and not is_admin:
            raise HTTPException(
                status_code=403,
                detail="คะแนนนี้ถูกบันทึกและล็อกแล้ว หากต้องการแก้ไขต้องส่งคำขออนุญาตจากประธานกรรมการก่อน",
            )

        reason_text = (req.edit_reason or "").strip()
        if not reason_text:
            raise HTTPException(
                status_code=400,
                detail="กรุณาระบุเหตุผลในการแก้ไขคะแนนในจุดที่ต้องการแก้ไข",
            )

        cursor.execute("""
        SELECT id, reviewed_by FROM edit_requests
        WHERE judge_id = ? AND competitor_id = ? AND status = 'approved'
        ORDER BY id DESC LIMIT 1
        """, (req.judge_id, req.competitor_id))
        approved_req = cursor.fetchone()
        approved_by = approved_req["reviewed_by"] if approved_req else (req.judge_id if is_admin else None)

        old_snapshot = {
            "art_1": existing["art_1"], "art_2": existing["art_2"], "art_3": existing["art_3"], "art_4": existing["art_4"],
            "ens_1": existing["ens_1"], "ens_2": existing["ens_2"], "ens_3": existing["ens_3"],
            "tech_1": existing["tech_1"], "tech_2": existing["tech_2"], "tech_3": existing["tech_3"],
            "artistic_score": existing["artistic_score"],
            "ensemble_score": existing["ensemble_score"],
            "technique_score": existing["technique_score"],
        }
        new_snapshot = {
            "art_1": req.art_1, "art_2": req.art_2, "art_3": req.art_3, "art_4": req.art_4,
            "ens_1": req.ens_1, "ens_2": req.ens_2, "ens_3": req.ens_3,
            "tech_1": req.tech_1, "tech_2": req.tech_2, "tech_3": req.tech_3,
            "artistic_score": artistic_score,
            "ensemble_score": ensemble_score,
            "technique_score": technique_score,
        }

        cursor.execute("""
        INSERT INTO score_edit_logs (judge_id, competitor_id, old_scores_json, new_scores_json, old_total, new_total, reason, edited_fields, approved_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            req.judge_id,
            req.competitor_id,
            json.dumps(old_snapshot, ensure_ascii=False),
            json.dumps(new_snapshot, ensure_ascii=False),
            existing["total_score"],
            total_score,
            reason_text,
            (req.edited_fields or "").strip(),
            approved_by,
        ))

        cursor.execute("""
        UPDATE scores SET
            art_1 = ?, art_2 = ?, art_3 = ?, art_4 = ?,
            ens_1 = ?, ens_2 = ?, ens_3 = ?,
            tech_1 = ?, tech_2 = ?, tech_3 = ?,
            artistic_score = ?, ensemble_score = ?, technique_score = ?, total_score = ?,
            comments = ?, is_locked = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (
            req.art_1, req.art_2, req.art_3, req.art_4,
            req.ens_1, req.ens_2, req.ens_3,
            req.tech_1, req.tech_2, req.tech_3,
            artistic_score, ensemble_score, technique_score, total_score,
            req.comments, existing["id"],
        ))

        if approved_req:
            cursor.execute("UPDATE edit_requests SET status = 'completed' WHERE id = ?", (approved_req["id"],))
    else:
        cursor.execute("""
        INSERT INTO scores (
            judge_id, competitor_id,
            art_1, art_2, art_3, art_4,
            ens_1, ens_2, ens_3,
            tech_1, tech_2, tech_3,
            artistic_score, ensemble_score, technique_score, total_score,
            comments, is_locked
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            req.judge_id, req.competitor_id,
            req.art_1, req.art_2, req.art_3, req.art_4,
            req.ens_1, req.ens_2, req.ens_3,
            req.tech_1, req.tech_2, req.tech_3,
            artistic_score, ensemble_score, technique_score, total_score,
            req.comments,
        ))

    conn.commit()
    return {
        "success": True,
        "total_score": total_score,
        "medal": get_medal(total_score),
    }


@app.post("/api/scores/request-edit")
def request_score_edit(req: EditRequestCreate, conn: sqlite3.Connection = Depends(get_db)):
    if not req.reason.strip():
        raise HTTPException(status_code=400, detail="กรุณาระบุเหตุผลในการขอแก้ไขคะแนน")

    cursor = conn.cursor()
    cursor.execute("SELECT id, is_locked FROM scores WHERE judge_id = ? AND competitor_id = ?", (req.judge_id, req.competitor_id))
    score_row = cursor.fetchone()
    if not score_row:
        raise HTTPException(status_code=404, detail="ยังไม่มีคะแนนที่บันทึกไว้สำหรับโรงเรียนนี้")
    if score_row["is_locked"] == 0:
        raise HTTPException(status_code=400, detail="คะแนนนี้ได้รับอนุญาตให้แก้ไขแล้ว สามารถกดแก้ไขคะแนนได้ทันที")

    cursor.execute("""
    SELECT id FROM edit_requests
    WHERE judge_id = ? AND competitor_id = ? AND status = 'pending'
    """, (req.judge_id, req.competitor_id))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="ท่านได้ส่งคำขอแก้ไขคะแนนรายการนี้ไปแล้ว กรุณารอประธานกรรมการอนุมัติ")

    cursor.execute("""
    INSERT INTO edit_requests (judge_id, competitor_id, reason, target_fields, status)
    VALUES (?, ?, ?, ?, 'pending')
    """, (req.judge_id, req.competitor_id, req.reason.strip(), (req.target_fields or "").strip()))
    conn.commit()
    return {"success": True, "message": "ส่งคำขออนุญาตแก้ไขคะแนนไปยังประธานกรรมการเรียบร้อยแล้ว"}


@app.get("/api/admin/edit-requests")
def list_edit_requests(conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("""
    SELECT er.*,
           j.fullname AS judge_name, j.school AS judge_school,
           c.school_name AS competitor_school, c.order_no AS competitor_order,
           cat.name AS category_name, cat.code AS category_code,
           s.total_score AS current_total_score
    FROM edit_requests er
    JOIN judges j ON er.judge_id = j.id
    JOIN competitors c ON er.competitor_id = c.id
    JOIN categories cat ON c.category_id = cat.id
    LEFT JOIN scores s ON (s.judge_id = er.judge_id AND s.competitor_id = er.competitor_id)
    ORDER BY CASE WHEN er.status = 'pending' THEN 0 ELSE 1 END, er.created_at DESC
    """)
    return [dict(row) for row in cursor.fetchall()]


@app.post("/api/admin/edit-requests/{request_id}/review")
def review_edit_request(request_id: int, req: EditRequestReview, conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM judges WHERE id = ?", (req.admin_id,))
    admin = cursor.fetchone()
    if not admin or not admin["is_admin"]:
        raise HTTPException(status_code=403, detail="เฉพาะประธานกรรมการเท่านั้นที่สามารถอนุมัติคำขอแก้ไขคะแนนได้")

    cursor.execute("SELECT * FROM edit_requests WHERE id = ?", (request_id,))
    er = cursor.fetchone()
    if not er:
        raise HTTPException(status_code=404, detail="ไม่พบคำขอแก้ไขคะแนน")
    if er["status"] != "pending":
        raise HTTPException(status_code=400, detail="คำขอนี้ได้รับการพิจารณาไปแล้ว")

    if req.action == "approve":
        cursor.execute("""
        UPDATE edit_requests
        SET status = 'approved', admin_note = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, ((req.admin_note or "").strip(), req.admin_id, request_id))

        cursor.execute("""
        UPDATE scores SET is_locked = 0
        WHERE judge_id = ? AND competitor_id = ?
        """, (er["judge_id"], er["competitor_id"]))
        msg = "อนุมัติให้กรรมการแก้ไขคะแนนเรียบร้อยแล้ว"
    elif req.action == "reject":
        cursor.execute("""
        UPDATE edit_requests
        SET status = 'rejected', admin_note = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, ((req.admin_note or "").strip(), req.admin_id, request_id))
        msg = "ปฏิเสธคำขอแก้ไขคะแนนแล้ว"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    conn.commit()
    return {"success": True, "message": msg}


# --- Summary & Audit Results ---
@app.get("/api/results")
def get_all_results(conn: sqlite3.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories ORDER BY id ASC")
    categories = [dict(row) for row in cursor.fetchall()]

    results_by_cat = []
    for cat in categories:
        cursor.execute("""
        SELECT j.id, j.fullname, j.position, j.school, cj.role, cj.order_no
        FROM category_judges cj
        JOIN judges j ON cj.judge_id = j.id
        WHERE cj.category_id = ?
        ORDER BY cj.order_no ASC
        """, (cat["id"],))
        cat_judges = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT * FROM competitors WHERE category_id = ? ORDER BY order_no ASC", (cat["id"],))
        comps = [dict(r) for r in cursor.fetchall()]

        cat_results = []
        for c in comps:
            cursor.execute("""
            SELECT s.judge_id, j.fullname, cj.role,
                   s.art_1, s.art_2, s.art_3, s.art_4,
                   s.ens_1, s.ens_2, s.ens_3,
                   s.tech_1, s.tech_2, s.tech_3,
                   s.artistic_score, s.ensemble_score, s.technique_score, s.total_score,
                   s.comments, s.is_locked, s.updated_at
            FROM scores s
            JOIN judges j ON s.judge_id = j.id
            JOIN category_judges cj ON (cj.judge_id = j.id AND cj.category_id = ?)
            WHERE s.competitor_id = ?
            ORDER BY cj.order_no ASC
            """, (cat["id"], c["id"]))
            scores_given = [dict(s) for s in cursor.fetchall()]

            cursor.execute("""
            SELECT sel.*, j.fullname AS judge_name, adm.fullname AS approved_by_name
            FROM score_edit_logs sel
            JOIN judges j ON sel.judge_id = j.id
            LEFT JOIN judges adm ON sel.approved_by = adm.id
            WHERE sel.competitor_id = ?
            ORDER BY sel.edited_at DESC
            """, (c["id"],))
            edit_logs = [dict(l) for l in cursor.fetchall()]

            if scores_given:
                n = len(scores_given)
                avg_total = round(sum(s["total_score"] for s in scores_given) / n, 2)
                avg_art = round(sum(s["artistic_score"] for s in scores_given) / n, 2)
                avg_ens = round(sum(s["ensemble_score"] for s in scores_given) / n, 2)
                avg_tech = round(sum(s["technique_score"] for s in scores_given) / n, 2)
            else:
                avg_total = avg_art = avg_ens = avg_tech = 0.0

            cat_results.append({
                "competitor": c,
                "scores_given": scores_given,
                "edit_logs": edit_logs,
                "judges_count": len(scores_given),
                "total_expected_judges": len(cat_judges),
                "avg_artistic": avg_art,
                "avg_ensemble": avg_ens,
                "avg_technique": avg_tech,
                "avg_total": avg_total,
                "medal": get_medal(avg_total) if scores_given else "-",
            })

        cat_results.sort(key=lambda x: x["avg_total"], reverse=True)
        for idx, item in enumerate(cat_results):
            item["rank"] = idx + 1 if item["scores_given"] else "-"

        results_by_cat.append({
            "category": cat,
            "judges": cat_judges,
            "competitors": cat_results,
        })

    return {"results": results_by_cat}


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
