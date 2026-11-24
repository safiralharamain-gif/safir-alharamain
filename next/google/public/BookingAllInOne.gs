/**
 * سفير الحرمين — نظام استقبال طلبات الحجز (ملف واحد)
 * يُنشر كمشروع Apps Script مستقل عن لوحة الإدارة.
 * يقرأ/يكتب فقط تبويب «طلبات الحجز» في شيت سفير الحرمين.
 */
const SAFIR_SHEET_ID = '1da0GKq95dzyeTd-hr6ceSoGq5IekUge17Vm-eopJMNw';
const SAFIR_BOOKINGS_TAB = 'طلبات الحجز';
const SAFIR_WHATSAPP = '201150337383';
const SAFIR_SERVICES = ['عمرة','حج','رحلات داخلية','فنادق','طيران','استفسار آخر'];

function doGet() {
  return HtmlService.createHtmlOutput(getBookingPage_())
    .setTitle('طلب حجز | سفير الحرمين')
    .addMetaTag('viewport','width=device-width,initial-scale=1');
}

function saveBooking(data) {
  if (!data || typeof data !== 'object') throw new Error('الطلب غير صحيح.');
  const text = (v,max) => String(v == null ? '' : v).trim().slice(0,max);
  const name = text(data.name,100), phone = text(data.phone,18);
  const service = text(data.service,50), date = text(data.date,10);
  const notes = text(data.notes,1000), website = text(data.website,100);
  if (website) throw new Error('تعذر استقبال الطلب.');
  if (data.agree !== true) throw new Error('يجب الموافقة على استخدام بياناتك للتواصل بخصوص الطلب.');
  if (name.length < 3) throw new Error('اكتب الاسم بالكامل.');
  if (!/^01[0125][0-9]{8}$/.test(phone) && !/^\+?[0-9]{10,15}$/.test(phone)) {
    throw new Error('اكتب رقم هاتف صحيح.');
  }
  if (!SAFIR_SERVICES.includes(service)) throw new Error('اختر الخدمة المطلوبة.');
  if (date && !/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new Error('تاريخ السفر غير صحيح.');
  const clean = (s) => /^[=+\-@\t\r]/.test(s) ? "'" + s : s;
  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    const sheet = SpreadsheetApp.openById(SAFIR_SHEET_ID).getSheetByName(SAFIR_BOOKINGS_TAB);
    if (!sheet) throw new Error('تبويب طلبات الحجز غير موجود.');
    const requestId = 'SAF-' + Utilities.getUuid().slice(0,8).toUpperCase();
    sheet.appendRow([requestId,new Date(),clean(name),"'"+phone,service,date,clean(notes),'جديد']);
    SpreadsheetApp.flush();
    return {ok:true,requestId:requestId};
  } finally {lock.releaseLock();}
}

function getBookingPage_() {
return String.raw`<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="UTF-8">
<style>
*{box-sizing:border-box}body{background:#f8f6ef;color:#174c40;font-family:Tahoma,Arial,sans-serif;margin:0;padding:18px}
main{max-width:620px;margin:0 auto;background:white;padding:28px;border-radius:16px;box-shadow:0 9px 30px #143b2c13}
h1{text-align:center;font-size:25px;margin:0 0 5px}p{text-align:center;color:#687a72}
label{display:block;font-weight:bold;margin:14px 0 5px}
input,select,textarea{width:100%;padding:12px;border:1px solid #c9d5d0;border-radius:9px;font:inherit}
input:focus,select:focus,textarea:focus{outline:2px solid #bb9a5d}
.agree{display:flex;gap:10px;align-items:flex-start;font-size:14px;font-weight:normal}.agree input{width:auto;margin-top:5px}
button,.wa{display:inline-block;margin-top:18px;background:#155b46;color:white;text-decoration:none;border:0;border-radius:10px;padding:13px 18px;font:inherit;cursor:pointer}
.wa{background:#188653}button:disabled{opacity:.5;cursor:wait}
#message{margin-top:18px;white-space:pre-wrap;font-weight:bold}.hint{font-size:13px}
</style></head><body><main>
<h1>🕋 سفير الحرمين</h1><p>طلب حجز أو استفسار — هنكلمك لتأكيد التفاصيل، وده مش تأكيد نهائي للحجز.</p>
<form id="form">
<label for="name">اسم العميل *</label><input id="name" name="name" required minlength="3" maxlength="100" autocomplete="name">
<label for="phone">رقم الهاتف *</label><input id="phone" name="phone" required inputmode="tel" autocomplete="tel">
<label for="service">الخدمة المطلوبة *</label><select id="service" name="service" required>
<option value="">اختار الخدمة</option><option>عمرة</option><option>حج</option><option>رحلات داخلية</option><option>فنادق</option><option>طيران</option><option>استفسار آخر</option>
</select>
<label for="date">تاريخ السفر المفضل</label><input id="date" name="date" type="date">
<label for="notes">تفاصيل الطلب</label><textarea id="notes" name="notes" maxlength="1000" rows="4"></textarea>
<input name="website" style="position:absolute;left:-9999px" autocomplete="off" tabindex="-1" aria-hidden="true">
<label class="agree"><input name="agree" type="checkbox" required> أوافق على استخدام بياناتي للتواصل بخصوص الطلب.</label>
<button id="send" type="submit">إرسال الطلب</button>
<a class="wa" href="https://wa.me/201150337383" target="_blank" rel="noopener noreferrer">تواصل واتساب</a>
</form><div id="message" role="status" aria-live="polite"></div>
<p class="hint">لا تدفع أي مبلغ لمجرد إرسال الطلب؛ فريق سفير الحرمين سيتواصل معك.</p>
</main>
<script>
const form=document.getElementById('form'),send=document.getElementById('send'),msg=document.getElementById('message');
form.addEventListener('submit',function(e){
 e.preventDefault();
 if(send.disabled)return;
 const data=Object.fromEntries(new FormData(form).entries());
 data.agree=form.elements.agree.checked;
 send.disabled=true;msg.textContent='جارٍ تسجيل الطلب...';
 google.script.run.withSuccessHandler(function(res){
   send.disabled=false;
   if(res && res.ok){
     msg.textContent='✅ تم تسجيل طلبك بنجاح.\nرقم الطلب: '+res.requestId+'\nسنتواصل معك لتأكيد التفاصيل.';
     form.reset();
   }else{msg.textContent='تعذر تسجيل الطلب، حاول مرة أخرى.';}
 }).withFailureHandler(function(err){
   send.disabled=false;
   msg.textContent='تعذر تسجيل الطلب: '+(err.message||'حاول مرة أخرى.');
 }).saveBooking(data);
});
</script></body></html>`;
}
