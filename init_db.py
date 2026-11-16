import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "scoring.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Judges table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS judges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE,
        email TEXT DEFAULT '',
        pin TEXT,
        fullname TEXT NOT NULL,
        position TEXT NOT NULL,
        school TEXT NOT NULL,
        is_admin BOOLEAN DEFAULT 0,
        is_verified INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Categories table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT NOT NULL,
        level TEXT NOT NULL
    )
    """)

    # Judge-Category mapping table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS category_judges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id TEXT NOT NULL,
        judge_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        order_no INTEGER NOT NULL,
        UNIQUE(category_id, judge_id),
        FOREIGN KEY (category_id) REFERENCES categories (id),
        FOREIGN KEY (judge_id) REFERENCES judges (id)
    )
    """)

    # Competitors table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS competitors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id TEXT NOT NULL,
        order_no INTEGER NOT NULL,
        school_name TEXT NOT NULL,
        affiliation_group TEXT NOT NULL,
        students_info TEXT,
        teachers_info TEXT,
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )
    """)

    # Detailed Scores table (10 sub-criteria x 10 pts = 100 pts)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        judge_id INTEGER NOT NULL,
        competitor_id INTEGER NOT NULL,
        art_1 REAL DEFAULT 0,
        art_2 REAL DEFAULT 0,
        art_3 REAL DEFAULT 0,
        art_4 REAL DEFAULT 0,
        ens_1 REAL DEFAULT 0,
        ens_2 REAL DEFAULT 0,
        ens_3 REAL DEFAULT 0,
        tech_1 REAL DEFAULT 0,
        tech_2 REAL DEFAULT 0,
        tech_3 REAL DEFAULT 0,
        artistic_score REAL DEFAULT 0,
        ensemble_score REAL DEFAULT 0,
        technique_score REAL DEFAULT 0,
        total_score REAL DEFAULT 0,
        comments TEXT DEFAULT '',
        is_locked INTEGER DEFAULT 1,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(judge_id, competitor_id),
        FOREIGN KEY (judge_id) REFERENCES judges (id),
        FOREIGN KEY (competitor_id) REFERENCES competitors (id)
    )
    """)

    # Score Edit Requests table (requires Chairman approval)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS edit_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        judge_id INTEGER NOT NULL,
        competitor_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        target_fields TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        admin_note TEXT DEFAULT '',
        reviewed_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reviewed_at TIMESTAMP,
        FOREIGN KEY (judge_id) REFERENCES judges (id),
        FOREIGN KEY (competitor_id) REFERENCES competitors (id),
        FOREIGN KEY (reviewed_by) REFERENCES judges (id)
    )
    """)

    # Score Edit Audit Logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS score_edit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        judge_id INTEGER NOT NULL,
        competitor_id INTEGER NOT NULL,
        old_scores_json TEXT NOT NULL,
        new_scores_json TEXT NOT NULL,
        old_total REAL NOT NULL,
        new_total REAL NOT NULL,
        reason TEXT NOT NULL,
        edited_fields TEXT DEFAULT '',
        approved_by INTEGER,
        edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (judge_id) REFERENCES judges (id),
        FOREIGN KEY (competitor_id) REFERENCES competitors (id),
        FOREIGN KEY (approved_by) REFERENCES judges (id)
    )
    """)

    # Seed categories
    categories = [
        ("various_m1_m6", "การแข่งขันวงดนตรีสากลเครื่องผสม (Various Ensemble) ม.๑ - ม.๖", "135", "ม.1 - ม.6"),
        ("wind_m1_m3", "การประกวดดนตรีประเภทวงดุริยางค์เครื่องลม (Wind Ensembles) ม.๑ - ม.๓", "649", "ม.1 - ม.3"),
        ("wind_m4_m6", "การประกวดดนตรีประเภทวงดุริยางค์เครื่องลม (Wind Ensembles) ม.๔ - ม.๖", "692", "ม.4 - ม.6")
    ]
    cursor.executemany("INSERT OR IGNORE INTO categories (id, name, code, level) VALUES (?, ?, ?, ?)", categories)

    # Seed Judges (Chairman has login phone & PIN; other judges verify via QR scan + Email & Phone)
    judges = [
        ("0956961606", "", "1234", "นายพงศธร โพธิแก้ว", "ครูโรงเรียนพะเยาพิทยาคม", "โรงเรียนพะเยาพิทยาคม", 1, 1),
        (None, "", "", "นายไกรลาศ คำเปิก", "ครูโรงเรียนราชประชานุเคราะห์ ๒๔ พะเยา", "โรงเรียนราชประชานุเคราะห์ ๒๔ พะเยา", 0, 0),
        (None, "", "", "นางสาวน้ำทิพย์ คงทน", "ครูโรงเรียนเชียงคำวิทยาคม", "โรงเรียนเชียงคำวิทยาคม", 0, 0),
        (None, "", "", "นายธนกฤต เทพมงคล", "ครูโรงเรียนเฉลิมพระเกียรติสมเด็จพระศรีนครินทร์ พะเยา", "โรงเรียนเฉลิมพระเกียรติสมเด็จพระศรีนครินทร์ พะเยา", 0, 0),
        (None, "", "", "นายชยุตพงษ์ วงค์เทพ", "ครูโรงเรียนพญาอลวิทยาคม", "โรงเรียนพญาอลวิทยาคม", 0, 0),
        (None, "", "", "นางสาวกมลทิพย์ วรรณวิจิตร", "ครูโรงเรียนแม่ใจวิทยาคม", "โรงเรียนแม่ใจวิทยาคม", 0, 0),
        (None, "", "", "นางสาวสุชานาถ อิงออน", "ครูโรงเรียนภูซางวิทยาคม", "โรงเรียนภูซางวิทยาคม", 0, 0),
    ]

    for j in judges:
        cursor.execute("""
        INSERT OR IGNORE INTO judges (phone, email, pin, fullname, position, school, is_admin, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, j)

    cursor.execute("SELECT id, fullname FROM judges")
    judge_map = {row[1]: row[0] for row in cursor.fetchall()}

    # Category-Judge assignments
    cat1_judges = [
        ("various_m1_m6", judge_map["นายพงศธร โพธิแก้ว"], "ประธานกรรมการ", 1),
        ("various_m1_m6", judge_map["นายไกรลาศ คำเปิก"], "กรรมการ", 2),
        ("various_m1_m6", judge_map["นางสาวน้ำทิพย์ คงทน"], "กรรมการ", 3),
        ("various_m1_m6", judge_map["นายธนกฤต เทพมงคล"], "กรรมการและเลขานุการ", 4),
    ]
    cursor.executemany("INSERT OR IGNORE INTO category_judges (category_id, judge_id, role, order_no) VALUES (?, ?, ?, ?)", cat1_judges)

    cat2_judges = [
        ("wind_m1_m3", judge_map["นายพงศธร โพธิแก้ว"], "ประธานกรรมการ", 1),
        ("wind_m1_m3", judge_map["นายชยุตพงษ์ วงค์เทพ"], "กรรมการ", 2),
        ("wind_m1_m3", judge_map["นางสาวน้ำทิพย์ คงทน"], "กรรมการ", 3),
        ("wind_m1_m3", judge_map["นางสาวกมลทิพย์ วรรณวิจิตร"], "กรรมการ", 4),
        ("wind_m1_m3", judge_map["นางสาวสุชานาถ อิงออน"], "กรรมการและเลขานุการ", 5),
    ]
    cursor.executemany("INSERT OR IGNORE INTO category_judges (category_id, judge_id, role, order_no) VALUES (?, ?, ?, ?)", cat2_judges)

    cat3_judges = [
        ("wind_m4_m6", judge_map["นายพงศธร โพธิแก้ว"], "ประธานกรรมการ", 1),
        ("wind_m4_m6", judge_map["นายชยุตพงษ์ วงค์เทพ"], "กรรมการ", 2),
        ("wind_m4_m6", judge_map["นางสาวน้ำทิพย์ คงทน"], "กรรมการ", 3),
        ("wind_m4_m6", judge_map["นางสาวกมลทิพย์ วรรณวิจิตร"], "กรรมการ", 4),
        ("wind_m4_m6", judge_map["นางสาวสุชานาถ อิงออน"], "กรรมการและเลขานุการ", 5),
    ]
    cursor.executemany("INSERT OR IGNORE INTO category_judges (category_id, judge_id, role, order_no) VALUES (?, ?, ?, ?)", cat3_judges)

    # Competitors
    competitors = [
        ("various_m1_m6", 1, "โรงเรียนสาธิตมหาวิทยาลัยพะเยา", "กลุ่ม 1 ภูกามยาว",
         "1. นายต้นบุญ สิทธิ์คงเชื้อ\n2. นายวสุพล กองสาย\n3. นายปฐพี รินคำ\n4. นางสาวกฤตพร บุญสูง\n5. นางสาวชนกภัท ปิติฐาโชติ",
         "1. นายชลวิทย์ บุญจันทร์"),

        ("wind_m1_m3", 1, "โรงเรียนดอกคำใต้วิทยาคม", "กลุ่ม 1 ภูกามยาว",
         "1. เด็กชายภูวดล ศรีวิชัย\n2. เด็กชายปวริศ ชาวน่าน\n3. นายมณฑล ทิพย์สุทธิ์\n4. เด็กชายวัชรพงศ์ คำมา\n5. เด็กชายชนม์ธนัช สามแปง\n6. เด็กชายจิรายุ สมศรี\n7. เด็กหญิงพิมนิกา จำรัส\n8. เด็กหญิงกรณัฐ พิลาลี\n9. เด็กหญิงพรภัชสรณ์ สังการ\n10. เด็กชายศวัส ใจหมั้น\n11. เด็กชายอดิกันต์ กันทะพงษ์\n12. เด็กชายปวรุตม์ อินออน",
         "1. นายวุฒิบูรณ์ ถูกนึก\n2. นายศิริชัย ธรรมศิริ\n3. นางสาวอริสรา แสงใส"),

        ("wind_m1_m3", 2, "โรงเรียนสาธิตมหาวิทยาลัยพะเยา", "กลุ่ม 1 ภูกามยาว",
         "1. เด็กหญิงชญานิศ กาวิละพันธ์\n2. เด็กหญิงเขมิกา จันดา\n3. นายวสุพล กองสาย\n4. เด็กชายภาสกร กันคำ\n5. เด็กชายธนวินท์ กมลจิตร์ประภา\n6. เด็กหญิงธมนันท์ อินทะนิล\n7. เด็กหญิงชนกานต์ ยะคำ\n8. เด็กหญิงสุภานดา ยะพรม\n9. นายต้นบุญ สิทธิ์คงเชื้อ\n10. เด็กชายณัฐกฤต มีมาก\n11. เด็กชายภวัตรพงศ์ สิริเจริญพานิช\n12. เด็กหญิงบัวบูชา ทาสกุล",
         "1. นายชลวิทย์ บุญจันทร์"),

        ("wind_m1_m3", 3, "โรงเรียนภูซางวิทยาคม", "กลุ่ม 2 ภูลังกา",
         "1. เด็กหญิงนิชาภา พึ่งพวก\n2. เด็กหญิงพรประภา ปวงผาบ\n3. เด็กหญิงพาขวัญ สถ่าน\n4. เด็กหญิงพิตติพันธ์ ถามะยะ\n5. เด็กหญิงรมิตา เรียบร้อย\n6. เด็กหญิงณัฐวรา แก้วชมแก้ว\n7. เด็กชายทัศดนัย ต๊ะอ้าย\n8. เด็กหญิงสุธินันท์ กิ่งแก้ว\n9. เด็กชายทิวัตถ์ ชุ่มตา\n10. เด็กชายปรัชญาริศร์ รวมสุข",
         "1. นายดุริยะ วงศ์ใหญ่\n2. นางสาวสว่างนภา นวลแก้ว\n3. นางสาวสุชานาถ อิงออน"),

        ("wind_m4_m6", 1, "โรงเรียนดอกคำใต้วิทยาคม", "กลุ่ม 1 ภูกามยาว",
         "1. นายภูวนาฏ คำนวล\n2. นายธเนศ จันทนะ\n3. นายเอกอมร สมศรี\n4. นายจักรินทร์ ศรีคำมูล\n5. นายกวินภพ ปัญญา\n6. นายสัณหนัฐ นามเมือง",
         "1. นายวุฒิบูรณ์ ถูกนึก\n2. นางสาวอังคณา ยะมงคล"),

        ("wind_m4_m6", 2, "โรงเรียนภูซางวิทยาคม", "กลุ่ม 2 ภูลังกา",
         "1. นายตะวัน จตุนาม\n2. นายพิรวิชญ์ เบิกบาน\n3. นายศุภฤกษ์ เบิกบาน\n4. นางสาวสิรินทรา รวมหมู่\n5. นางสาวสุพิชญนันท์ อุปธิ\n6. นายรัฐพล สุหเจริญชัย\n7. นายกิตติศักดิ์ สุขสงวน\n8. นายรัฐภูมิ เย็นใจ\n9. นายปฏิพล บุญแรง",
         "1. นายดุริยะ วงศ์ใหญ่\n2. นางสาวสว่างนภา นวลแก้ว\n3. นางสาวสุชานาถ อิงออน")
    ]

    cursor.execute("SELECT COUNT(*) FROM competitors")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
        INSERT INTO competitors (category_id, order_no, school_name, affiliation_group, students_info, teachers_info)
        VALUES (?, ?, ?, ?, ?, ?)
        """, competitors)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    print("Database re-initialized with detailed rubric & edit approval schema.")
