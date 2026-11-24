/**
 * سفير الحرمين — حجوزات العمرة الأصلية كاملة
 * استبدل به محتوى المشروع المستقل "سفير الحرمين - الحجوزات"
 * ثم: Deploy > Manage deployments > Edit > New version > Deploy
 * الإتاحة العامة لا تتم إلا بعد إعداد حماية مناسبة واختبار صلاحيات النشر.
 */
const SAFIR_SPREADSHEET_ID='1da0GKq95dzyeTd-hr6ceSoGq5IekUge17Vm-eopJMNw';
const SAFIR_TAB='طلبات الحجز';
const SAFIR_WA='201150337383';
const TYPES=['عمرة','حج','رحلات داخلية','فنادق','طيران','استفسار آخر'];
const FIELDS=['name','phone','address','governorate','tripName','date','adults','children','room','meals','payment','notes','source','service'];
function h_(s){return String(s||'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));}
function doGet(e){
  const p=e&&e.parameter||{};
  const pre={};FIELDS.forEach(k=>pre[k]=String(p[k]||'').slice(0,k==='notes'?900:120));
  const page=page_().replace('/*PREFILL_DATA*/','const PREFILL='+JSON.stringify(pre).replace(/</g,'\\u003c')+';');
  return HtmlService.createHtmlOutput(page).setTitle('حجز العمرة | سفير الحرمين').addMetaTag('viewport','width=device-width,initial-scale=1');
}
function saveBooking(d){
 if(!d||typeof d!=='object')throw Error('الطلب غير صحيح.');
 const t=(k,n)=>String(d[k]??'').trim().slice(0,n);
 if(t('website',50))throw Error('تعذر استقبال الطلب.');
 if(d.agree!==true)throw Error('يجب الموافقة على استخدام البيانات للتواصل بخصوص الحجز.');
 const name=t('name',100),phone=t('phone',20),service=t('service',40)||'عمرة';
 if(name.length<3)throw Error('اكتب الاسم بالكامل.');
 if(!/^01[0125]\d{8}$/.test(phone) && !/^\+?\d{10,15}$/.test(phone))throw Error('اكتب رقم هاتف صحيح.');
 if(!TYPES.includes(service))throw Error('نوع الخدمة غير صحيح.');
 const adults=t('adults',3),children=t('children',3);
 if([adults,children].some(n=>n&&!/^\d{1,3}$/.test(n)))throw Error('عدد الأفراد يجب أن يكون رقمًا.');
 const clean=s=>/^[=+\-@\t\r]/.test(s)?"'"+s:s;
 const details=[
   ['العنوان',t('address',120)],['المحافظة',t('governorate',80)],
   ['الرحلة',t('tripName',120)],['الكبار',adults],['الأطفال',children],
   ['الغرفة',t('room',60)],['الوجبات',t('meals',40)],
   ['طريقة الدفع',t('payment',50)],['عرفنا من',t('source',80)],
   ['ملاحظات',t('notes',900)]
 ].filter(([k,v])=>v).map(([k,v])=>k+': '+v).join(' | ');
 const lock=LockService.getScriptLock();lock.waitLock(15000);
 try{
  const sheet=SpreadsheetApp.openById(SAFIR_SPREADSHEET_ID).getSheetByName(SAFIR_TAB);
  if(!sheet)throw Error('تبويب طلبات الحجز غير موجود.');
  const id='SAF-'+Utilities.getUuid().slice(0,8).toUpperCase();
  sheet.appendRow([id,new Date(),clean(name),"'"+phone,service,clean(t('date',30)),clean(details),'جديد']);
  SpreadsheetApp.flush();
  return {ok:true,requestId:id};
 }finally{lock.releaseLock();}
}
function page_(){return String.raw`<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0;background:#f8f6ef;color:#184b40;font:16px Tahoma,Arial,sans-serif;padding:20px}
main{max-width:760px;background:white;margin:auto;border-radius:20px;padding:26px;box-shadow:0 12px 34px #16463311}
h1{text-align:center;margin:0 0 10px}p{line-height:1.8}.muted{color:#637870;text-align:center}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}label{display:block;font-weight:bold;margin:10px 0 5px}
input,select,textarea{width:100%;padding:12px;border:1px solid #cbd8d2;border-radius:9px;font:inherit}
textarea{resize:vertical}.wide{grid-column:1/-1}.agree{display:flex;gap:8px;font-weight:normal}.agree input{width:auto}
button,.wa{border:0;border-radius:10px;padding:13px 20px;margin-top:12px;font:inherit;cursor:pointer;color:white;background:#145844}
button:disabled{opacity:.5}.wa{display:inline-block;background:#1a8669;text-decoration:none}
#status{font-weight:bold;white-space:pre-wrap;margin-top:16px}.fine{font-size:13px;color:#6d6d6d}
@media(max-width:650px){.grid{grid-template-columns:1fr}.wide{grid-column:auto}main{padding:18px}}
</style></head><body><main><h1>🕋 سفير الحرمين</h1>
<p class="muted">طلب حجز العمرة — سجل بياناتك، وسيتم التواصل معك للتأكيد. إرسال الطلب ليس حجزًا نهائيًا أو مطالبة بالدفع.</p>
<form id="form" class="grid">
<div><label>اسم العميل *</label><input name="name" required minlength="3" maxlength="100" autocomplete="name"></div>
<div><label>الموبايل *</label><input name="phone" required inputmode="tel" autocomplete="tel"></div>
<div><label>العنوان</label><input name="address" maxlength="120"></div>
<div><label>المحافظة</label><input name="governorate" maxlength="80"></div>
<div><label>الرحلة</label><input name="tripName" maxlength="120"></div>
<div><label>تاريخ الرحلة</label><input name="date" placeholder="يوم / شهر / سنة" maxlength="30"></div>
<div><label>عدد الكبار</label><input name="adults" type="number" min="0" max="999"></div>
<div><label>عدد الأطفال</label><input name="children" type="number" min="0" max="999"></div>
<div><label>نوع الغرفة</label><select name="room"><option value="">اختار</option><option>خماسي</option><option>خماسي / رباعي</option><option selected>رباعي</option><option>ثلاثي</option><option>ثنائي</option></select></div>
<div><label>الوجبات</label><select name="meals"><option>لا</option><option>نعم</option></select></div>
<div><label>طريقة الدفع المفضلة</label><select name="payment"><option>كاش</option><option>محفظة كاش</option><option>تحويل بنكي</option><option>فيزا</option></select></div>
<div><label>عرفتنا منين؟</label><select name="source"><option>صديق رشحنا ليك</option><option>عن طريق الفيسبوك</option><option>عن طريق الواتساب</option><option>عن طريق الموقع</option><option>عميل سابق</option></select></div>
<div class="wide"><label>رسالة أو استفسار</label><textarea name="notes" rows="3" maxlength="900"></textarea></div>
<div class="wide"><label class="agree"><input type="checkbox" name="agree" required> أوافق على استخدام بياناتي للتواصل بخصوص الطلب.</label></div>
<input name="website" style="position:absolute;left:-9999px" tabindex="-1" autocomplete="off" aria-hidden="true">
<input type="hidden" name="service" value="عمرة">
<div class="wide"><button id="submit" type="submit">تسجيل طلب الحجز</button> <a class="wa" href="https://wa.me/201150337383" target="_blank" rel="noopener noreferrer">واتساب</a></div>
</form><div id="status" aria-live="polite"></div><p class="fine">سفير الحرمين | 01150337383</p></main>
<script>
/*PREFILL_DATA*/
const f=document.getElementById('form'),b=document.getElementById('submit'),s=document.getElementById('status');
Object.keys(PREFILL).forEach(k=>{const el=f.elements.namedItem(k);if(el&&PREFILL[k])el.value=PREFILL[k]});
f.addEventListener('submit',e=>{
 e.preventDefault();if(b.disabled)return;
 const d=Object.fromEntries(new FormData(f).entries());d.agree=f.elements.agree.checked;
 b.disabled=true;s.textContent='جارٍ تسجيل طلبك...';
 google.script.run.withSuccessHandler(r=>{
  b.disabled=false;
  if(!r||!r.ok){s.textContent='تعذر إكمال الطلب';return;}
  s.textContent='✅ تم تسجيل الطلب\nرقم الطلب: '+r.requestId+'\nسنتواصل معك لتأكيد التفاصيل.';
  f.reset();
 }).withFailureHandler(err=>{b.disabled=false;s.textContent='لم يكتمل التسجيل: '+(err.message||'حاول مرة أخرى');}).saveBooking(d);
});
</script></body></html>`;}
