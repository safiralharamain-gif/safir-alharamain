/**
 * سفير الحرمين - واجهة حجز عامة مستقلة
 * أنشئ مشروع Apps Script جديدًا (منفصلًا عن مشروع لوحة الإدارة).
 * عيّن Script Property باسم SHEET_ID إلى معرّف جدول الإدارة.
 * انشر هذا المشروع وحده كتطبيق ويب يعمل بصلاحية المالك.
 */
function doGet(){
  return HtmlService.createHtmlOutputFromFile('Booking').setTitle('طلب حجز | سفير الحرمين').addMetaTag('viewport','width=device-width, initial-scale=1');
}
function submitBooking(data){
  if(!data || typeof data!=='object') throw new Error('طلب غير صحيح');
  const name=String(data.name||'').trim(),phone=String(data.phone||'').trim();
  const service=String(data.service||'').trim(),travelDate=String(data.travel_date||'');
  const notes=String(data.notes||'').trim();
  if(name.length<3||name.length>100||!/^\+?[0-9 \-]{10,18}$/.test(phone)||!['عمرة','حج','رحلة داخلية','فنادق','طيران','استفسار آخر'].includes(service))throw new Error('راجع الاسم ورقم الهاتف والخدمة');
  if(notes.length>1000||!/^(|\d{4}-\d{2}-\d{2})$/.test(travelDate)||data.consent!==true)throw new Error('راجع البيانات والموافقة');
  const token=String(data.website||'');if(token) throw new Error('تعذر إرسال الطلب');
  const sheetId=PropertiesService.getScriptProperties().getProperty('SHEET_ID');
  if(!sheetId)throw new Error('الخدمة غير مفعلة بعد');
  const lock=LockService.getScriptLock();lock.waitLock(20000);
  try{
    const ss=SpreadsheetApp.openById(sheetId);
    const sh=ss.getSheetByName('Bookings');
    if(!sh)throw new Error('قاعدة بيانات الحجوزات غير مهيأة');
    const id=Utilities.getUuid();
    const clean=x=>x.startsWith('=')||x.startsWith('+')||x.startsWith('-')||x.startsWith('@')?"'"+x:x;
    sh.appendRow([id,new Date().toISOString(),clean(name),"'"+phone,service,travelDate,clean(notes),'new']);
    return {ok:true,id};
  } finally{lock.releaseLock()}
}
