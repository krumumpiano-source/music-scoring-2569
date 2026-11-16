/**
 * ระบบลงคะแนนการแข่งขันวงดนตรี - งานศิลปหัตถกรรมนักเรียน ครั้งที่ 74 ปีการศึกษา 2569 จังหวัดพะเยา
 * Backend API powered by Google Apps Script + Google Sheets
 */

function jsonResponse_(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

function getSs_() {
  return SpreadsheetApp.getActiveSpreadsheet();
}

function nowIso_() {
  return Utilities.formatDate(new Date(), 'Asia/Bangkok', 'yyyy-MM-dd HH:mm:ss');
}

function getMedal_(score) {
  if (score >= 80) return 'เหรียญทอง';
  if (score >= 70) return 'เหรียญเงิน';
  if (score >= 60) return 'เหรียญทองแดง';
  return 'เกียรติบัตรเข้าร่วม';
}

function ensureSheet_(ss, name, headers) {
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold').setBackground('#f1f5f9');
    sheet.setFrozenRows(1);
    sheet.getRange(1, 1, sheet.getMaxRows(), headers.length).setNumberFormat('@');
  }
  return sheet;
}

function sheetToObjects_(sheet) {
  const data = sheet.getDataRange().getDisplayValues();
  if (data.length <= 1) return [];
  const headers = data[0];
  const rows = [];
  for (let i = 1; i < data.length; i++) {
    const obj = { _row: i + 1 };
    for (let j = 0; j < headers.length; j++) {
      obj[headers[j]] = data[i][j];
    }
    rows.push(obj);
  }
  return rows;
}

function appendRowAsText_(sheet, rowArray) {
  const nextRow = sheet.getLastRow() + 1;
  const range = sheet.getRange(nextRow, 1, 1, rowArray.length);
  range.setNumberFormat('@');
  range.setValues([rowArray.map(v => v === null || v === undefined ? '' : String(v))]);
  return nextRow;
}

function updateRowCell_(sheet, rowNum, colIndex, value) {
  const cell = sheet.getRange(rowNum, colIndex);
  cell.setNumberFormat('@');
  cell.setValue(value === null || value === undefined ? '' : String(value));
}

function ensureSeeded_() {
  const ss = getSs_();
  const initialized = ss.getSheetByName('judges') && ss.getSheetByName('competitors') && ss.getSheetByName('scores');

  const judgesSheet = ensureSheet_(ss, 'judges', ['id', 'phone', 'email', 'pin', 'fullname', 'position', 'school', 'is_admin', 'is_verified', 'created_at']);
  const catsSheet = ensureSheet_(ss, 'categories', ['id', 'name', 'code', 'level']);
  const cjSheet = ensureSheet_(ss, 'category_judges', ['id', 'category_id', 'judge_id', 'role', 'order_no']);
  const compSheet = ensureSheet_(ss, 'competitors', ['id', 'category_id', 'order_no', 'school_name', 'affiliation_group', 'students_info', 'teachers_info']);
  ensureSheet_(ss, 'scores', [
    'id', 'judge_id', 'competitor_id',
    'art_1', 'art_2', 'art_3', 'art_4',
    'ens_1', 'ens_2', 'ens_3',
    'tech_1', 'tech_2', 'tech_3',
    'artistic_score', 'ensemble_score', 'technique_score', 'total_score',
    'comments', 'is_locked', 'submitted_at', 'updated_at'
  ]);
  ensureSheet_(ss, 'edit_requests', ['id', 'judge_id', 'competitor_id', 'reason', 'target_fields', 'status', 'admin_note', 'reviewed_by', 'created_at', 'reviewed_at']);
  ensureSheet_(ss, 'score_edit_logs', ['id', 'judge_id', 'competitor_id', 'old_scores_json', 'new_scores_json', 'old_total', 'new_total', 'reason', 'edited_fields', 'approved_by', 'edited_at']);

  if (initialized && judgesSheet.getLastRow() > 1) return;

  const now = nowIso_();

  if (judgesSheet.getLastRow() <= 1) {
    const judges = [
      ['1', '0956961606', '', '1234', 'นายพงศธร โพธิแก้ว', 'ครูโรงเรียนพะเยาพิทยาคม', 'โรงเรียนพะเยาพิทยาคม', '1', '1', now],
      ['2', '', '', '', 'นายไกรลาศ คำเปิก', 'ครูโรงเรียนราชประชานุเคราะห์ ๒๔ พะเยา', 'โรงเรียนราชประชานุเคราะห์ ๒๔ พะเยา', '0', '0', now],
      ['3', '', '', '', 'นางสาวน้ำทิพย์ คงทน', 'ครูโรงเรียนเชียงคำวิทยาคม', 'โรงเรียนเชียงคำวิทยาคม', '0', '0', now],
      ['4', '', '', '', 'นายธนกฤต เทพมงคล', 'ครูโรงเรียนเฉลิมพระเกียรติสมเด็จพระศรีนครินทร์ พะเยา', 'โรงเรียนเฉลิมพระเกียรติสมเด็จพระศรีนครินทร์ พะเยา', '0', '0', now],
      ['5', '', '', '', 'นายชยุตพงษ์ วงค์เทพ', 'ครูโรงเรียนพญาอลวิทยาคม', 'โรงเรียนพญาอลวิทยาคม', '0', '0', now],
      ['6', '', '', '', 'นางสาวกมลทิพย์ วรรณวิจิตร', 'ครูโรงเรียนแม่ใจวิทยาคม', 'โรงเรียนแม่ใจวิทยาคม', '0', '0', now],
      ['7', '', '', '', 'นางสาวสุชานาถ อิงออน', 'ครูโรงเรียนภูซางวิทยาคม', 'โรงเรียนภูซางวิทยาคม', '0', '0', now]
    ];
    judges.forEach(r => appendRowAsText_(judgesSheet, r));
  }

  if (catsSheet.getLastRow() <= 1) {
    const cats = [
      ['various_m1_m6', 'การแข่งขันวงดนตรีสากลเครื่องผสม (Various Ensemble) ม.๑ - ม.๖', '135', 'ม.1 - ม.6'],
      ['wind_m1_m3', 'การประกวดดนตรีประเภทวงดุริยางค์เครื่องลม (Wind Ensembles) ม.๑ - ม.๓', '649', 'ม.1 - ม.3'],
      ['wind_m4_m6', 'การประกวดดนตรีประเภทวงดุริยางค์เครื่องลม (Wind Ensembles) ม.๔ - ม.๖', '692', 'ม.4 - ม.6']
    ];
    cats.forEach(r => appendRowAsText_(catsSheet, r));
  }

  if (cjSheet.getLastRow() <= 1) {
    const cjs = [
      ['1', 'various_m1_m6', '1', 'ประธานกรรมการ', '1'],
      ['2', 'various_m1_m6', '2', 'กรรมการ', '2'],
      ['3', 'various_m1_m6', '3', 'กรรมการ', '3'],
      ['4', 'various_m1_m6', '4', 'กรรมการและเลขานุการ', '4'],

      ['5', 'wind_m1_m3', '1', 'ประธานกรรมการ', '1'],
      ['6', 'wind_m1_m3', '5', 'กรรมการ', '2'],
      ['7', 'wind_m1_m3', '3', 'กรรมการ', '3'],
      ['8', 'wind_m1_m3', '6', 'กรรมการ', '4'],
      ['9', 'wind_m1_m3', '7', 'กรรมการและเลขานุการ', '5'],

      ['10', 'wind_m4_m6', '1', 'ประธานกรรมการ', '1'],
      ['11', 'wind_m4_m6', '5', 'กรรมการ', '2'],
      ['12', 'wind_m4_m6', '3', 'กรรมการ', '3'],
      ['13', 'wind_m4_m6', '6', 'กรรมการ', '4'],
      ['14', 'wind_m4_m6', '7', 'กรรมการและเลขานุการ', '5']
    ];
    cjs.forEach(r => appendRowAsText_(cjSheet, r));
  }

  if (compSheet.getLastRow() <= 1) {
    const comps = [
      ['1', 'various_m1_m6', '1', 'โรงเรียนสาธิตมหาวิทยาลัยพะเยา', 'กลุ่ม 1 ภูกามยาว',
       '1. นายต้นบุญ สิทธิ์คงเชื้อ\n2. นายวสุพล กองสาย\n3. นายปฐพี รินคำ\n4. นางสาวกฤตพร บุญสูง\n5. นางสาวชนกภัท ปิติฐาโชติ',
       '1. นายชลวิทย์ บุญจันทร์'],

      ['2', 'wind_m1_m3', '1', 'โรงเรียนดอกคำใต้วิทยาคม', 'กลุ่ม 1 ภูกามยาว',
       '1. เด็กชายภูวดล ศรีวิชัย\n2. เด็กชายปวริศ ชาวน่าน\n3. นายมณฑล ทิพย์สุทธิ์\n4. เด็กชายวัชรพงศ์ คำมา\n5. เด็กชายชนม์ธนัช สามแปง\n6. เด็กชายจิรายุ สมศรี\n7. เด็กหญิงพิมนิกา จำรัส\n8. เด็กหญิงกรณัฐ พิลาลี\n9. เด็กหญิงพรภัชสรณ์ สังการ\n10. เด็กชายศวัส ใจหมั้น\n11. เด็กชายอดิกันต์ กันทะพงษ์\n12. เด็กชายปวรุตม์ อินออน',
       '1. นายวุฒิบูรณ์ ถูกนึก\n2. นายศิริชัย ธรรมศิริ\n3. นางสาวอริสรา แสงใส'],

      ['3', 'wind_m1_m3', '2', 'โรงเรียนสาธิตมหาวิทยาลัยพะเยา', 'กลุ่ม 1 ภูกามยาว',
       '1. เด็กหญิงชญานิศ กาวิละพันธ์\n2. เด็กหญิงเขมิกา จันดา\n3. นายวสุพล กองสาย\n4. เด็กชายภาสกร กันคำ\n5. เด็กชายธนวินท์ กมลจิตร์ประภา\n6. เด็กหญิงธมนันท์ อินทะนิล\n7. เด็กหญิงชนกานต์ ยะคำ\n8. เด็กหญิงสุภานดา ยะพรม\n9. นายต้นบุญ สิทธิ์คงเชื้อ\n10. เด็กชายณัฐกฤต มีมาก\n11. เด็กชายภวัตรพงศ์ สิริเจริญพานิช\n12. เด็กหญิงบัวบูชา ทาสกุล',
       '1. นายชลวิทย์ บุญจันทร์'],

      ['4', 'wind_m1_m3', '3', 'โรงเรียนภูซางวิทยาคม', 'กลุ่ม 2 ภูลังกา',
       '1. เด็กหญิงนิชาภา พึ่งพวก\n2. เด็กหญิงพรประภา ปวงผาบ\n3. เด็กหญิงพาขวัญ สถ่าน\n4. เด็กหญิงพิตติพันธ์ ถามะยะ\n5. เด็กหญิงรมิตา เรียบร้อย\n6. เด็กหญิงณัฐวรา แก้วชมแก้ว\n7. เด็กชายทัศดนัย ต๊ะอ้าย\n8. เด็กหญิงสุธินันท์ กิ่งแก้ว\n9. เด็กชายทิวัตถ์ ชุ่มตา\n10. เด็กชายปรัชญาริศร์ รวมสุข',
       '1. นายดุริยะ วงศ์ใหญ่\n2. นางสาวสว่างนภา นวลแก้ว\n3. นางสาวสุชานาถ อิงออน'],

      ['5', 'wind_m4_m6', '1', 'โรงเรียนดอกคำใต้วิทยาคม', 'กลุ่ม 1 ภูกามยาว',
       '1. นายภูวนาฏ คำนวล\n2. นายธเนศ จันทนะ\n3. นายเอกอมร สมศรี\n4. นายจักรินทร์ ศรีคำมูล\n5. นายกวินภพ ปัญญา\n6. นายสัณหนัฐ นามเมือง',
       '1. นายวุฒิบูรณ์ ถูกนึก\n2. นางสาวอังคณา ยะมงคล'],

      ['6', 'wind_m4_m6', '2', 'โรงเรียนภูซางวิทยาคม', 'กลุ่ม 2 ภูลังกา',
       '1. นายตะวัน จตุนาม\n2. นายพิรวิชญ์ เบิกบาน\n3. นายศุภฤกษ์ เบิกบาน\n4. นางสาวสิรินทรา รวมหมู่\n5. นางสาวสุพิชญนันท์ อุปธิ\n6. นายรัฐพล สุหเจริญชัย\n7. นายกิตติศักดิ์ สุขสงวน\n8. นายรัฐภูมิ เย็นใจ\n9. นายปฏิพล บุญแรง',
       '1. นายดุริยะ วงศ์ใหญ่\n2. นางสาวสว่างนภา นวลแก้ว\n3. นางสาวสุชานาถ อิงออน']
    ];
    comps.forEach(r => appendRowAsText_(compSheet, r));
  }
}

function doGet(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    ensureSeeded_();
    const p = (e && e.parameter) || {};
    const action = p.action || 'health';

    if (action === 'health') {
      return jsonResponse_({ ok: true, status: 'ready' });
    }
    if (action === 'judges') {
      return jsonResponse_({ ok: true, data: handleGetJudges_() });
    }
    if (action === 'categories') {
      return jsonResponse_({ ok: true, data: handleGetCategories_(p.judge_id) });
    }
    if (action === 'category_info') {
      return jsonResponse_({ ok: true, data: handleGetCategoryInfo_(p.category_id) });
    }
    if (action === 'competitors') {
      return jsonResponse_({ ok: true, data: handleGetCompetitors_(p.category_id, p.judge_id) });
    }
    if (action === 'edit_requests') {
      return jsonResponse_({ ok: true, data: handleListEditRequests_() });
    }
    if (action === 'results') {
      return jsonResponse_({ ok: true, data: handleGetResults_() });
    }
    return jsonResponse_({ ok: false, detail: 'Unknown GET action: ' + action });
  } catch (err) {
    return jsonResponse_({ ok: false, detail: err.message || String(err) });
  } finally {
    lock.releaseLock();
  }
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    ensureSeeded_();
    const body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    const action = body.action || '';

    if (action === 'login') {
      return jsonResponse_(handleLogin_(body));
    }
    if (action === 'qr_checkin') {
      return jsonResponse_(handleQrCheckin_(body));
    }
    if (action === 'update_pin') {
      return jsonResponse_(handleUpdatePin_(body));
    }
    if (action === 'admin_update_judge') {
      return jsonResponse_(handleAdminUpdateJudge_(body));
    }
    if (action === 'submit_score') {
      return jsonResponse_(handleSubmitScore_(body));
    }
    if (action === 'request_edit') {
      return jsonResponse_(handleRequestEdit_(body));
    }
    if (action === 'review_edit_request') {
      return jsonResponse_(handleReviewEditRequest_(body));
    }
    if (action === 'add_competitor') {
      return jsonResponse_(handleAddCompetitor_(body));
    }
    if (action === 'delete_competitor') {
      return jsonResponse_(handleDeleteCompetitor_(body));
    }
    return jsonResponse_({ ok: false, detail: 'Unknown POST action: ' + action });
  } catch (err) {
    return jsonResponse_({ ok: false, detail: err.message || String(err) });
  } finally {
    lock.releaseLock();
  }
}

// --- Handlers ---
function handleGetJudges_() {
  const ss = getSs_();
  return sheetToObjects_(ss.getSheetByName('judges')).map(j => ({
    id: Number(j.id),
    phone: j.phone || '',
    email: j.email || '',
    fullname: j.fullname,
    position: j.position,
    school: j.school,
    is_admin: j.is_admin === '1',
    is_verified: Number(j.is_verified || 0)
  }));
}

function handleLogin_(body) {
  const phone = String(body.phone || '').trim();
  const pin = String(body.pin || '').trim();
  const ss = getSs_();
  const judges = sheetToObjects_(ss.getSheetByName('judges'));
  const judge = judges.find(j => String(j.phone || '').trim() === phone);

  if (!judge || judge.is_admin !== '1') {
    return {
      ok: false,
      detail: 'เฉพาะประธานกรรมการเท่านั้นที่เข้าสู่ระบบหน้านี้ กรรมการท่านอื่นกรุณาสแกน QR Code จากประธานกรรมการ'
    };
  }
  if (judge.pin && judge.pin !== pin) {
    return { ok: false, detail: 'รหัส PIN ไม่ถูกต้อง' };
  }
  return {
    ok: true,
    success: true,
    judge: {
      id: Number(judge.id),
      phone: judge.phone,
      email: judge.email || '',
      fullname: judge.fullname,
      position: judge.position,
      school: judge.school,
      is_admin: true
    }
  };
}

function handleQrCheckin_(body) {
  const categoryId = String(body.category_id || '').trim();
  const judgeId = Number(body.judge_id);
  const phone = String(body.phone || '').trim();
  const email = String(body.email || '').trim();

  if (!phone || phone.length < 9) {
    return { ok: false, detail: 'กรุณากรอกเบอร์โทรศัพท์ให้ถูกต้อง (อย่างน้อย 9 หลัก)' };
  }
  if (!email || email.indexOf('@') === -1) {
    return { ok: false, detail: 'กรุณากรอกอีเมลให้ถูกต้อง' };
  }

  const ss = getSs_();
  const judgesSheet = ss.getSheetByName('judges');
  const judges = sheetToObjects_(judgesSheet);
  const cjs = sheetToObjects_(ss.getSheetByName('category_judges'));

  const cj = cjs.find(x => x.category_id === categoryId && Number(x.judge_id) === judgeId);
  if (!cj) {
    return { ok: false, detail: 'ไม่พบรายชื่อกรรมการท่านนี้ในรายการแข่งขันที่เลือก' };
  }
  const judge = judges.find(j => Number(j.id) === judgeId);
  if (!judge) {
    return { ok: false, detail: 'ไม่พบข้อมูลกรรมการ' };
  }

  if (judge.is_admin === '1') {
    if (phone !== String(judge.phone || '').trim()) {
      return { ok: false, detail: 'เบอร์โทรศัพท์ของประธานกรรมการไม่ถูกต้อง' };
    }
    if (email && !judge.email) {
      updateRowCell_(judgesSheet, judge._row, 3, email);
    }
  } else {
    if (Number(judge.is_verified || 0) === 0) {
      const duplicate = judges.find(j => Number(j.id) !== judgeId && String(j.phone || '').trim() === phone);
      if (duplicate) {
        return { ok: false, detail: 'เบอร์โทรศัพท์นี้ถูกใช้งานโดยกรรมการท่านอื่นแล้ว' };
      }
      updateRowCell_(judgesSheet, judge._row, 2, phone);
      updateRowCell_(judgesSheet, judge._row, 3, email);
      updateRowCell_(judgesSheet, judge._row, 9, '1');
    } else {
      const savedPhone = String(judge.phone || '').trim();
      const savedEmail = String(judge.email || '').trim().toLowerCase();
      if (phone !== savedPhone || email.toLowerCase() !== savedEmail) {
        return {
          ok: false,
          detail: 'รายชื่อกรรมการนี้ได้ลงทะเบียนยืนยันตัวตนแล้ว ข้อมูลเบอร์โทรหรืออีเมลไม่ตรงกัน (หากพิมพ์ผิดกรุณาแจ้งประธานกรรมการเพื่อรีเซ็ต)'
        };
      }
    }
  }

  return {
    ok: true,
    success: true,
    judge: {
      id: Number(judge.id),
      phone: phone,
      email: email,
      fullname: judge.fullname,
      position: judge.position,
      school: judge.school,
      is_admin: judge.is_admin === '1',
      role: cj.role
    }
  };
}

function handleUpdatePin_(body) {
  const judgeId = Number(body.judge_id);
  const oldPin = String(body.old_pin || '').trim();
  const newPin = String(body.new_pin || '').trim();
  const ss = getSs_();
  const judgesSheet = ss.getSheetByName('judges');
  const judges = sheetToObjects_(judgesSheet);
  const judge = judges.find(j => Number(j.id) === judgeId);

  if (!judge) return { ok: false, detail: 'ไม่พบข้อมูลกรรมการ' };
  if (judge.pin && judge.pin !== oldPin) return { ok: false, detail: 'รหัส PIN เดิมไม่ถูกต้อง' };

  updateRowCell_(judgesSheet, judge._row, 4, newPin);
  return { ok: true, success: true, message: 'เปลี่ยนรหัส PIN สำเร็จ' };
}

function handleAdminUpdateJudge_(body) {
  const adminId = Number(body.admin_id);
  const judgeId = Number(body.judge_id);
  const ss = getSs_();
  const judgesSheet = ss.getSheetByName('judges');
  const judges = sheetToObjects_(judgesSheet);

  const admin = judges.find(j => Number(j.id) === adminId);
  if (!admin || admin.is_admin !== '1') {
    return { ok: false, detail: 'เฉพาะประธานกรรมการ / แอดมินเท่านั้น' };
  }
  const target = judges.find(j => Number(j.id) === judgeId);
  if (!target) return { ok: false, detail: 'ไม่พบข้อมูลกรรมการ' };

  if (body.reset_verification) {
    if (target.is_admin === '1') {
      return { ok: false, detail: 'ไม่สามารถรีเซ็ตประธานกรรมการได้' };
    }
    updateRowCell_(judgesSheet, target._row, 2, '');
    updateRowCell_(judgesSheet, target._row, 3, '');
    updateRowCell_(judgesSheet, target._row, 9, '0');
    return {
      ok: true,
      success: true,
      message: 'รีเซ็ตการยืนยันตัวตนของกรรมการเรียบร้อยแล้ว กรรมการสามารถสแกน QR กรอกเบอร์โทรและอีเมลใหม่ได้'
    };
  }
  return { ok: true, success: true, message: 'อัปเดตข้อมูลเรียบร้อยแล้ว' };
}

function handleGetCategories_(judgeIdParam) {
  const judgeId = judgeIdParam ? Number(judgeIdParam) : null;
  const ss = getSs_();
  const cats = sheetToObjects_(ss.getSheetByName('categories'));
  const comps = sheetToObjects_(ss.getSheetByName('competitors'));
  const cjs = sheetToObjects_(ss.getSheetByName('category_judges'));
  const judges = sheetToObjects_(ss.getSheetByName('judges'));
  const scores = sheetToObjects_(ss.getSheetByName('scores'));

  const judgeMap = {};
  judges.forEach(j => { judgeMap[Number(j.id)] = j; });

  return cats.map(cat => {
    const catComps = comps.filter(c => c.category_id === cat.id);
    const catCjs = cjs
      .filter(x => x.category_id === cat.id)
      .sort((a, b) => Number(a.order_no) - Number(b.order_no))
      .map(x => {
        const j = judgeMap[Number(x.judge_id)] || {};
        return {
          id: Number(j.id),
          fullname: j.fullname || '',
          school: j.school || '',
          position: j.position || '',
          is_verified: Number(j.is_verified || 0),
          is_admin: j.is_admin === '1',
          role: x.role,
          order_no: Number(x.order_no)
        };
      });

    let isAssigned = true;
    let judgeRole = null;
    let scoredCount = 0;

    if (judgeId) {
      const found = catCjs.find(x => x.id === judgeId);
      isAssigned = !!found;
      judgeRole = found ? found.role : null;
      const compIds = catComps.map(c => Number(c.id));
      scoredCount = scores.filter(s => Number(s.judge_id) === judgeId && compIds.indexOf(Number(s.competitor_id)) !== -1).length;
    }

    return {
      id: cat.id,
      name: cat.name,
      code: cat.code,
      level: cat.level,
      total_competitors: catComps.length,
      judges: catCjs,
      is_assigned: isAssigned,
      judge_role: judgeRole,
      scored_competitors: scoredCount
    };
  });
}

function handleGetCategoryInfo_(categoryId) {
  const all = handleGetCategories_(null);
  const found = all.find(c => c.id === categoryId);
  if (!found) throw new Error('ไม่พบรายการแข่งขันนี้');
  return found;
}

function handleGetCompetitors_(categoryId, judgeIdParam) {
  const judgeId = judgeIdParam ? Number(judgeIdParam) : null;
  const ss = getSs_();
  const comps = sheetToObjects_(ss.getSheetByName('competitors'))
    .filter(c => c.category_id === categoryId)
    .sort((a, b) => Number(a.order_no) - Number(b.order_no));
  const scores = sheetToObjects_(ss.getSheetByName('scores'));
  const editReqs = sheetToObjects_(ss.getSheetByName('edit_requests'));
  const editLogs = sheetToObjects_(ss.getSheetByName('score_edit_logs'));

  return comps.map(c => {
    const cid = Number(c.id);
    const s = judgeId ? scores.find(x => Number(x.judge_id) === judgeId && Number(x.competitor_id) === cid) : null;

    let latestReq = null;
    let compLogs = [];
    if (judgeId) {
      const reqs = editReqs
        .filter(r => Number(r.judge_id) === judgeId && Number(r.competitor_id) === cid)
        .sort((a, b) => Number(b.id) - Number(a.id));
      if (reqs.length > 0) {
        latestReq = {
          id: Number(reqs[0].id),
          reason: reqs[0].reason,
          target_fields: reqs[0].target_fields,
          status: reqs[0].status,
          admin_note: reqs[0].admin_note,
          created_at: reqs[0].created_at,
          reviewed_at: reqs[0].reviewed_at
        };
      }
      compLogs = editLogs
        .filter(l => Number(l.judge_id) === judgeId && Number(l.competitor_id) === cid)
        .sort((a, b) => Number(b.id) - Number(a.id))
        .map(l => ({
          id: Number(l.id),
          old_total: Number(l.old_total),
          new_total: Number(l.new_total),
          reason: l.reason,
          edited_fields: l.edited_fields,
          edited_at: l.edited_at
        }));
    }

    return {
      id: cid,
      category_id: c.category_id,
      order_no: Number(c.order_no),
      school_name: c.school_name,
      affiliation_group: c.affiliation_group,
      students_info: c.students_info,
      teachers_info: c.teachers_info,
      score_id: s ? Number(s.id) : null,
      art_1: s ? Number(s.art_1) : null,
      art_2: s ? Number(s.art_2) : null,
      art_3: s ? Number(s.art_3) : null,
      art_4: s ? Number(s.art_4) : null,
      ens_1: s ? Number(s.ens_1) : null,
      ens_2: s ? Number(s.ens_2) : null,
      ens_3: s ? Number(s.ens_3) : null,
      tech_1: s ? Number(s.tech_1) : null,
      tech_2: s ? Number(s.tech_2) : null,
      tech_3: s ? Number(s.tech_3) : null,
      artistic_score: s ? Number(s.artistic_score) : null,
      ensemble_score: s ? Number(s.ensemble_score) : null,
      technique_score: s ? Number(s.technique_score) : null,
      total_score: s ? Number(s.total_score) : null,
      comments: s ? s.comments : '',
      is_locked: s ? Number(s.is_locked) : 1,
      is_scored: !!s,
      latest_edit_request: latestReq,
      edit_logs: compLogs
    };
  });
}

function handleSubmitScore_(body) {
  const judgeId = Number(body.judge_id);
  const compId = Number(body.competitor_id);
  const subKeys = ['art_1', 'art_2', 'art_3', 'art_4', 'ens_1', 'ens_2', 'ens_3', 'tech_1', 'tech_2', 'tech_3'];
  const vals = {};

  for (let i = 0; i < subKeys.length; i++) {
    const k = subKeys[i];
    const v = Number(body[k]);
    if (isNaN(v) || v < 0 || v > 10) {
      return { ok: false, detail: 'คะแนนหัวข้อย่อย (' + k + ') ต้องอยู่ระหว่าง 0 - 10 คะแนน' };
    }
    vals[k] = v;
  }

  const artScore = Math.round((vals.art_1 + vals.art_2 + vals.art_3 + vals.art_4) * 100) / 100;
  const ensScore = Math.round((vals.ens_1 + vals.ens_2 + vals.ens_3) * 100) / 100;
  const techScore = Math.round((vals.tech_1 + vals.tech_2 + vals.tech_3) * 100) / 100;
  const totalScore = Math.round((artScore + ensScore + techScore) * 100) / 100;

  const ss = getSs_();
  const judges = sheetToObjects_(ss.getSheetByName('judges'));
  const judge = judges.find(j => Number(j.id) === judgeId);
  if (!judge) return { ok: false, detail: 'ไม่พบข้อมูลกรรมการ' };
  const isAdmin = judge.is_admin === '1';

  const scoresSheet = ss.getSheetByName('scores');
  const scores = sheetToObjects_(scoresSheet);
  const existing = scores.find(s => Number(s.judge_id) === judgeId && Number(s.competitor_id) === compId);
  const now = nowIso_();

  if (existing) {
    if (Number(existing.is_locked) === 1 && !isAdmin) {
      return {
        ok: false,
        detail: 'คะแนนนี้ถูกบันทึกและล็อกแล้ว หากต้องการแก้ไขต้องส่งคำขออนุญาตจากประธานกรรมการก่อน'
      };
    }
    const reasonText = String(body.edit_reason || '').trim();
    if (!reasonText) {
      return { ok: false, detail: 'กรุณาระบุเหตุผลในการแก้ไขคะแนนในจุดที่ต้องการแก้ไข' };
    }

    const reqsSheet = ss.getSheetByName('edit_requests');
    const reqs = sheetToObjects_(reqsSheet)
      .filter(r => Number(r.judge_id) === judgeId && Number(r.competitor_id) === compId && r.status === 'approved')
      .sort((a, b) => Number(b.id) - Number(a.id));
    const approvedReq = reqs.length > 0 ? reqs[0] : null;
    const approvedBy = approvedReq ? approvedReq.reviewed_by : (isAdmin ? String(judgeId) : '');

    const oldSnap = {
      art_1: Number(existing.art_1), art_2: Number(existing.art_2), art_3: Number(existing.art_3), art_4: Number(existing.art_4),
      ens_1: Number(existing.ens_1), ens_2: Number(existing.ens_2), ens_3: Number(existing.ens_3),
      tech_1: Number(existing.tech_1), tech_2: Number(existing.tech_2), tech_3: Number(existing.tech_3),
      artistic_score: Number(existing.artistic_score),
      ensemble_score: Number(existing.ensemble_score),
      technique_score: Number(existing.technique_score)
    };
    const newSnap = {
      art_1: vals.art_1, art_2: vals.art_2, art_3: vals.art_3, art_4: vals.art_4,
      ens_1: vals.ens_1, ens_2: vals.ens_2, ens_3: vals.ens_3,
      tech_1: vals.tech_1, tech_2: vals.tech_2, tech_3: vals.tech_3,
      artistic_score: artScore,
      ensemble_score: ensScore,
      technique_score: techScore
    };

    const logsSheet = ss.getSheetByName('score_edit_logs');
    const nextLogId = sheetToObjects_(logsSheet).length + 1;
    appendRowAsText_(logsSheet, [
      nextLogId, judgeId, compId,
      JSON.stringify(oldSnap), JSON.stringify(newSnap),
      existing.total_score, totalScore,
      reasonText, String(body.edited_fields || '').trim(),
      approvedBy, now
    ]);

    const updatedRow = [
      existing.id, judgeId, compId,
      vals.art_1, vals.art_2, vals.art_3, vals.art_4,
      vals.ens_1, vals.ens_2, vals.ens_3,
      vals.tech_1, vals.tech_2, vals.tech_3,
      artScore, ensScore, techScore, totalScore,
      String(body.comments || '').trim(), '1', existing.submitted_at, now
    ];
    const range = scoresSheet.getRange(existing._row, 1, 1, updatedRow.length);
    range.setNumberFormat('@');
    range.setValues([updatedRow.map(v => String(v))]);

    if (approvedReq) {
      updateRowCell_(reqsSheet, approvedReq._row, 6, 'completed');
    }
  } else {
    const nextId = scores.length + 1;
    appendRowAsText_(scoresSheet, [
      nextId, judgeId, compId,
      vals.art_1, vals.art_2, vals.art_3, vals.art_4,
      vals.ens_1, vals.ens_2, vals.ens_3,
      vals.tech_1, vals.tech_2, vals.tech_3,
      artScore, ensScore, techScore, totalScore,
      String(body.comments || '').trim(), '1', now, now
    ]);
  }

  return {
    ok: true,
    success: true,
    total_score: totalScore,
    medal: getMedal_(totalScore)
  };
}

function handleRequestEdit_(body) {
  const judgeId = Number(body.judge_id);
  const compId = Number(body.competitor_id);
  const reason = String(body.reason || '').trim();
  const targetFields = String(body.target_fields || '').trim();

  if (!reason) return { ok: false, detail: 'กรุณาระบุเหตุผลในการขอแก้ไขคะแนน' };

  const ss = getSs_();
  const scores = sheetToObjects_(ss.getSheetByName('scores'));
  const scoreRow = scores.find(s => Number(s.judge_id) === judgeId && Number(s.competitor_id) === compId);
  if (!scoreRow) return { ok: false, detail: 'ยังไม่มีคะแนนที่บันทึกไว้สำหรับโรงเรียนนี้' };
  if (Number(scoreRow.is_locked) === 0) {
    return { ok: false, detail: 'คะแนนนี้ได้รับอนุญาตให้แก้ไขแล้ว สามารถกดแก้ไขคะแนนได้ทันที' };
  }

  const reqsSheet = ss.getSheetByName('edit_requests');
  const reqs = sheetToObjects_(reqsSheet);
  const pending = reqs.find(r => Number(r.judge_id) === judgeId && Number(r.competitor_id) === compId && r.status === 'pending');
  if (pending) {
    return { ok: false, detail: 'ท่านได้ส่งคำขอแก้ไขคะแนนรายการนี้ไปแล้ว กรุณารอประธานกรรมการอนุมัติ' };
  }

  const nextId = reqs.length + 1;
  appendRowAsText_(reqsSheet, [
    nextId, judgeId, compId, reason, targetFields, 'pending', '', '', nowIso_(), ''
  ]);
  return { ok: true, success: true, message: 'ส่งคำขออนุญาตแก้ไขคะแนนไปยังประธานกรรมการเรียบร้อยแล้ว' };
}

function handleListEditRequests_() {
  const ss = getSs_();
  const reqs = sheetToObjects_(ss.getSheetByName('edit_requests'));
  const judges = sheetToObjects_(ss.getSheetByName('judges'));
  const comps = sheetToObjects_(ss.getSheetByName('competitors'));
  const cats = sheetToObjects_(ss.getSheetByName('categories'));
  const scores = sheetToObjects_(ss.getSheetByName('scores'));

  const judgeMap = {};
  judges.forEach(j => { judgeMap[Number(j.id)] = j; });
  const compMap = {};
  comps.forEach(c => { compMap[Number(c.id)] = c; });
  const catMap = {};
  cats.forEach(c => { catMap[c.id] = c; });

  return reqs
    .map(r => {
      const j = judgeMap[Number(r.judge_id)] || {};
      const c = compMap[Number(r.competitor_id)] || {};
      const cat = catMap[c.category_id] || {};
      const s = scores.find(x => Number(x.judge_id) === Number(r.judge_id) && Number(x.competitor_id) === Number(r.competitor_id));
      return {
        id: Number(r.id),
        judge_id: Number(r.judge_id),
        competitor_id: Number(r.competitor_id),
        reason: r.reason,
        target_fields: r.target_fields,
        status: r.status,
        admin_note: r.admin_note,
        reviewed_by: r.reviewed_by ? Number(r.reviewed_by) : null,
        created_at: r.created_at,
        reviewed_at: r.reviewed_at,
        judge_name: j.fullname || '',
        judge_school: j.school || '',
        competitor_school: c.school_name || '',
        competitor_order: Number(c.order_no || 0),
        category_name: cat.name || '',
        category_code: cat.code || '',
        current_total_score: s ? Number(s.total_score) : 0
      };
    })
    .sort((a, b) => {
      if (a.status === 'pending' && b.status !== 'pending') return -1;
      if (a.status !== 'pending' && b.status === 'pending') return 1;
      return b.id - a.id;
    });
}

function handleReviewEditRequest_(body) {
  const requestId = Number(body.request_id);
  const adminId = Number(body.admin_id);
  const action = body.action;
  const adminNote = String(body.admin_note || '').trim();

  const ss = getSs_();
  const judges = sheetToObjects_(ss.getSheetByName('judges'));
  const admin = judges.find(j => Number(j.id) === adminId);
  if (!admin || admin.is_admin !== '1') {
    return { ok: false, detail: 'เฉพาะประธานกรรมการเท่านั้นที่สามารถอนุมัติคำขอแก้ไขคะแนนได้' };
  }

  const reqsSheet = ss.getSheetByName('edit_requests');
  const reqs = sheetToObjects_(reqsSheet);
  const er = reqs.find(r => Number(r.id) === requestId);
  if (!er) return { ok: false, detail: 'ไม่พบคำขอแก้ไขคะแนน' };
  if (er.status !== 'pending') return { ok: false, detail: 'คำขอนี้ได้รับการพิจารณาไปแล้ว' };

  const now = nowIso_();
  if (action === 'approve') {
    updateRowCell_(reqsSheet, er._row, 6, 'approved');
    updateRowCell_(reqsSheet, er._row, 7, adminNote);
    updateRowCell_(reqsSheet, er._row, 8, adminId);
    updateRowCell_(reqsSheet, er._row, 10, now);

    const scoresSheet = ss.getSheetByName('scores');
    const scores = sheetToObjects_(scoresSheet);
    const sc = scores.find(s => Number(s.judge_id) === Number(er.judge_id) && Number(s.competitor_id) === Number(er.competitor_id));
    if (sc) {
      updateRowCell_(scoresSheet, sc._row, 19, '0');
    }
    return { ok: true, success: true, message: 'อนุมัติให้กรรมการแก้ไขคะแนนเรียบร้อยแล้ว' };
  } else if (action === 'reject') {
    updateRowCell_(reqsSheet, er._row, 6, 'rejected');
    updateRowCell_(reqsSheet, er._row, 7, adminNote);
    updateRowCell_(reqsSheet, er._row, 8, adminId);
    updateRowCell_(reqsSheet, er._row, 10, now);
    return { ok: true, success: true, message: 'ปฏิเสธคำขอแก้ไขคะแนนแล้ว' };
  }
  return { ok: false, detail: 'Invalid action' };
}

function handleGetResults_() {
  const ss = getSs_();
  const cats = sheetToObjects_(ss.getSheetByName('categories'));
  const cjs = sheetToObjects_(ss.getSheetByName('category_judges'));
  const judges = sheetToObjects_(ss.getSheetByName('judges'));
  const comps = sheetToObjects_(ss.getSheetByName('competitors'));
  const scores = sheetToObjects_(ss.getSheetByName('scores'));
  const logs = sheetToObjects_(ss.getSheetByName('score_edit_logs'));

  const judgeMap = {};
  judges.forEach(j => { judgeMap[Number(j.id)] = j; });

  const resultsByCat = cats.map(cat => {
    const catJudges = cjs
      .filter(x => x.category_id === cat.id)
      .sort((a, b) => Number(a.order_no) - Number(b.order_no))
      .map(x => {
        const j = judgeMap[Number(x.judge_id)] || {};
        return {
          id: Number(j.id),
          fullname: j.fullname || '',
          position: j.position || '',
          school: j.school || '',
          role: x.role,
          order_no: Number(x.order_no)
        };
      });

    const catJudgeOrder = {};
    catJudges.forEach(cj => { catJudgeOrder[cj.id] = cj; });

    const catComps = comps
      .filter(c => c.category_id === cat.id)
      .sort((a, b) => Number(a.order_no) - Number(b.order_no));

    const catResults = catComps.map(c => {
      const cid = Number(c.id);
      const given = scores
        .filter(s => Number(s.competitor_id) === cid)
        .map(s => {
          const jid = Number(s.judge_id);
          const cjInfo = catJudgeOrder[jid] || {};
          const jInfo = judgeMap[jid] || {};
          return {
            judge_id: jid,
            fullname: jInfo.fullname || '',
            role: cjInfo.role || '',
            order_no: cjInfo.order_no || 99,
            art_1: Number(s.art_1), art_2: Number(s.art_2), art_3: Number(s.art_3), art_4: Number(s.art_4),
            ens_1: Number(s.ens_1), ens_2: Number(s.ens_2), ens_3: Number(s.ens_3),
            tech_1: Number(s.tech_1), tech_2: Number(s.tech_2), tech_3: Number(s.tech_3),
            artistic_score: Number(s.artistic_score),
            ensemble_score: Number(s.ensemble_score),
            technique_score: Number(s.technique_score),
            total_score: Number(s.total_score),
            comments: s.comments || '',
            is_locked: Number(s.is_locked),
            updated_at: s.updated_at
          };
        })
        .sort((a, b) => a.order_no - b.order_no);

      const compLogs = logs
        .filter(l => Number(l.competitor_id) === cid)
        .sort((a, b) => Number(b.id) - Number(a.id))
        .map(l => ({
          id: Number(l.id),
          judge_name: (judgeMap[Number(l.judge_id)] || {}).fullname || '',
          approved_by_name: (judgeMap[Number(l.approved_by)] || {}).fullname || '',
          old_total: Number(l.old_total),
          new_total: Number(l.new_total),
          reason: l.reason,
          edited_fields: l.edited_fields,
          edited_at: l.edited_at
        }));

      let avgTotal = 0, avgArt = 0, avgEns = 0, avgTech = 0;
      if (given.length > 0) {
        const n = given.length;
        avgTotal = Math.round((given.reduce((sum, x) => sum + x.total_score, 0) / n) * 100) / 100;
        avgArt = Math.round((given.reduce((sum, x) => sum + x.artistic_score, 0) / n) * 100) / 100;
        avgEns = Math.round((given.reduce((sum, x) => sum + x.ensemble_score, 0) / n) * 100) / 100;
        avgTech = Math.round((given.reduce((sum, x) => sum + x.technique_score, 0) / n) * 100) / 100;
      }

      return {
        competitor: {
          id: cid,
          category_id: c.category_id,
          order_no: Number(c.order_no),
          school_name: c.school_name,
          affiliation_group: c.affiliation_group
        },
        scores_given: given,
        edit_logs: compLogs,
        judges_count: given.length,
        total_expected_judges: catJudges.length,
        avg_artistic: avgArt,
        avg_ensemble: avgEns,
        avg_technique: avgTech,
        avg_total: avgTotal,
        medal: given.length > 0 ? getMedal_(avgTotal) : '-'
      };
    });

    catResults.sort((a, b) => b.avg_total - a.avg_total);
    catResults.forEach((item, idx) => {
      item.rank = item.scores_given.length > 0 ? idx + 1 : '-';
    });

    return {
      category: { id: cat.id, name: cat.name, code: cat.code, level: cat.level },
      judges: catJudges,
      competitors: catResults
    };
  });

  return { results: resultsByCat };
}

function handleAddCompetitor_(body) {
  const adminId = Number(body.admin_id);
  const categoryId = String(body.category_id || '').trim();
  const schoolName = String(body.school_name || '').trim();
  const affiliationGroup = String(body.affiliation_group || '').trim() || '-';
  const studentsInfo = String(body.students_info || '').trim();
  const teachersInfo = String(body.teachers_info || '').trim();
  let orderNo = Number(body.order_no || 0);

  if (!schoolName) {
    return { ok: false, detail: 'กรุณากรอกชื่อโรงเรียน หรือชื่อวงดนตรี' };
  }

  const ss = getSs_();
  const judges = sheetToObjects_(ss.getSheetByName('judges'));
  const admin = judges.find(j => Number(j.id) === adminId);
  if (!admin || admin.is_admin !== '1') {
    return { ok: false, detail: 'เฉพาะประธานกรรมการ / แอดมินเท่านั้นที่สามารถเพิ่มวงหรือโรงเรียนได้' };
  }

  const cats = sheetToObjects_(ss.getSheetByName('categories'));
  if (!cats.find(c => c.id === categoryId)) {
    return { ok: false, detail: 'ไม่พบรายการแข่งขันที่เลือก' };
  }

  const compSheet = ss.getSheetByName('competitors');
  const comps = sheetToObjects_(compSheet);
  const maxId = comps.reduce((m, c) => Math.max(m, Number(c.id || 0)), 0);
  const nextId = maxId + 1;

  if (!orderNo || orderNo <= 0) {
    const catComps = comps.filter(c => c.category_id === categoryId);
    const maxOrder = catComps.reduce((m, c) => Math.max(m, Number(c.order_no || 0)), 0);
    orderNo = maxOrder + 1;
  }

  appendRowAsText_(compSheet, [
    nextId,
    categoryId,
    orderNo,
    schoolName,
    affiliationGroup,
    studentsInfo,
    teachersInfo
  ]);

  return {
    ok: true,
    success: true,
    message: 'เพิ่มวง / โรงเรียนเข้าแข่งขันเรียบร้อยแล้ว',
    competitor: {
      id: nextId,
      category_id: categoryId,
      order_no: orderNo,
      school_name: schoolName,
      affiliation_group: affiliationGroup
    }
  };
}

function handleDeleteCompetitor_(body) {
  const adminId = Number(body.admin_id);
  const compId = Number(body.competitor_id);

  const ss = getSs_();
  const judges = sheetToObjects_(ss.getSheetByName('judges'));
  const admin = judges.find(j => Number(j.id) === adminId);
  if (!admin || admin.is_admin !== '1') {
    return { ok: false, detail: 'เฉพาะประธานกรรมการ / แอดมินเท่านั้น' };
  }

  const scores = sheetToObjects_(ss.getSheetByName('scores'));
  if (scores.some(s => Number(s.competitor_id) === compId)) {
    return { ok: false, detail: 'ไม่สามารถลบโรงเรียนที่มีกรรมการลงคะแนนแล้วได้' };
  }

  const compSheet = ss.getSheetByName('competitors');
  const comps = sheetToObjects_(compSheet);
  const target = comps.find(c => Number(c.id) === compId);
  if (!target) {
    return { ok: false, detail: 'ไม่พบข้อมูลโรงเรียนที่ต้องการลบ' };
  }

  compSheet.deleteRow(target._row);
  return { ok: true, success: true, message: 'ลบรายชื่อโรงเรียนเรียบร้อยแล้ว' };
}

