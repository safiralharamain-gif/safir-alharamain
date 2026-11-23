/**
 * سفير الحرمين - لوحة الإدارة العربية
 * ضع هذا الكود في Apps Script مرتبط بملف Google Sheets خاص.
 * لا تنشر هذا المشروع كتطبيق ويب للجمهور.
 */
const TABS = {
  Offers: ['id','title','price','departure_date','duration_days','hotel','description','status','updated_at'],
  Bookings: ['id','created_at','name','phone','service','travel_date','notes','status'],
  Settings: ['key','value']
};
function onOpen() {
  SpreadsheetApp.getUi().createMenu('سفير الحرمين')
    .addItem('فتح لوحة الإدارة', 'openSafirAdmin')
    .addItem('تهيئة الجداول', 'setupSafirSheets').addToUi();
}
function setupSafirSheets() {
  const ss=SpreadsheetApp.getActiveSpreadsheet();
  Object.keys(TABS).forEach(name=>{
    let sheet=ss.getSheetByName(name)||ss.insertSheet(name);
    if(sheet.getLastRow()===0) sheet.appendRow(TABS[name]);
    sheet.setFrozenRows(1);
    sheet.setRightToLeft(true);
  });
  const s=ss.getSheetByName('Settings');
  if(s.getLastRow()===1) s.appendRow(['whatsapp','201150337383']);
  SpreadsheetApp.getUi().alert('تم تجهيز الجداول الثلاثة. لا تشارك ملف الحجوزات مع الجمهور.');
}
function openSafirAdmin(){
  SpreadsheetApp.getUi().showSidebar(HtmlService.createHtmlOutputFromFile('Sidebar').setTitle('لوحة سفير الحرمين'));
}
function getTab_(name){
  if(!TABS[name]) throw new Error('جدول غير مسموح');
  const sheet=SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name);
  if(!sheet) throw new Error('شغّل تهيئة الجداول أولاً');
  return sheet;
}
function rows_(name){
  const sh=getTab_(name),v=sh.getDataRange().getValues(),cols=TABS[name];
  return v.slice(1).filter(r=>r[0]).map(r=>Object.fromEntries(cols.map((k,i)=>[k,r[i] instanceof Date?Utilities.formatDate(r[i],Session.getScriptTimeZone(),'yyyy-MM-dd'):r[i]])));
}
function getDashboardData(){
  const offers=rows_('Offers'),bookings=rows_('Bookings');
  return {offers,bookings,totals:{offers:offers.length,active:offers.filter(x=>x.status==='published').length,bookings:bookings.length,newBookings:bookings.filter(x=>x.status==='new').length}};
}
function saveOffer(data){
  if(!data || typeof data!=='object') throw new Error('بيانات غير صحيحة');
  const title=String(data.title||'').trim().slice(0,120);
  const price=Number(data.price);
  const status=String(data.status||'draft');
  if(!title || !Number.isFinite(price) || price<0) throw new Error('اسم العرض والسعر مطلوبان');
  if(!['draft','published','hidden','expired'].includes(status)) throw new Error('حالة غير صالحة');
  const sh=getTab_('Offers'), existing=rows_('Offers');
  const id=data.id && existing.some(x=>x.id===data.id)?String(data.id):Utilities.getUuid();
  const values=[id,title,price,String(data.departure_date||''),Number(data.duration_days)||0,String(data.hotel||'').slice(0,150),String(data.description||'').slice(0,2000),status,new Date().toISOString()];
  const rowIndex=existing.findIndex(x=>x.id===id);
  if(rowIndex>=0) sh.getRange(rowIndex+2,1,1,values.length).setValues([values]); else sh.appendRow(values);
  return {ok:true,id};
}
function setBookingStatus(id,status) {
  if(!['new','contacted','confirmed','cancelled'].includes(status)) throw new Error('حالة غير صحيحة');
  const sh=getTab_('Bookings'),rows=rows_('Bookings'),i=rows.findIndex(x=>x.id===id);
  if(i<0) throw new Error('الحجز غير موجود');
  sh.getRange(i+2,8).setValue(status);
  return {ok:true};
}
