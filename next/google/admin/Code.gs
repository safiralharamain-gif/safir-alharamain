/**
 * سفير الحرمين | لوحة الإدارة V3
 * تطبيق مرتبط بملف Google Sheets الخاص بالإدارة.
 * لا تنشر هذا المشروع كتطبيق ويب عام: جميع دوال الإدارة خاصة بالمحررين في الملف.
 * تبويب الحجوزات وملفات العملاء لا تتم مشاركتهما مع الجمهور.
 */
const SAFIR = {
  offersTab:'عروض العمرة', bookingsTab:'طلبات الحجز',
  mediaFolderProperty:'SAFIR_MEDIA_FOLDER_ID',
  whatsapp:'201150337383'
};
function onOpen(){
 SpreadsheetApp.getUi().createMenu('سفير الحرمين')
  .addItem('فتح لوحة التحكم الاحترافية','openSafirAdmin')
  .addItem('تجهيز أعمدة الصور','setupSafirMedia').addToUi();
}
function openSafirAdmin(){
 setupSafirMedia();
 const out=HtmlService.createHtmlOutputFromFile('Sidebar')
   .setTitle('سفير الحرمين | لوحة الإدارة')
   .setWidth(1260).setHeight(790);
 SpreadsheetApp.getUi().showModelessDialog(out,'سفير الحرمين — إدارة العروض والحجوزات');
}
function sheet_(name){
 const sh=SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name);
 if(!sh)throw Error('الجدول المطلوب غير موجود: '+name);
 return sh;
}
function setupSafirMedia(){
 const sh=sheet_(SAFIR.offersTab);
 if(sh.getMaxColumns()<12)sh.insertColumnsAfter(sh.getMaxColumns(),12-sh.getMaxColumns());
 ['الصورة الرئيسية','معرض الصور','بيانات إضافية'].forEach((v,i)=>{
  if(!sh.getRange(1,i+10).getValue())sh.getRange(1,i+10).setValue(v);
 });
 sh.setFrozenRows(1);sh.setRightToLeft(true);
}
function str_(v,n){return String(v==null?'':v).trim().slice(0,n||200);}
function plain_(v,n){
 const s=str_(v,n);
 return /^[\s]*[=+\-@\t\r]/.test(s)?"'"+s:s;
}
function date_(v){
 if(v instanceof Date)return Utilities.formatDate(v,Session.getScriptTimeZone(),'yyyy-MM-dd');
 return str_(v,40);
}
function parseJson_(v,fallback){try{return JSON.parse(String(v||''))||fallback}catch(_){return fallback}}
function imageUrl_(v){
 const s=str_(v,1000);
 if(!s)return '';
 try{
  const u=new URL(s);
  return u.protocol==='https:'?s:'';
 }catch(_){return '';}
}
function cleanGallery_(gallery){
 return (Array.isArray(gallery)?gallery:[]).slice(0,12).map(x=>({
  fileId:str_(x&&x.fileId,120).replace(/[^-\w]/g,''),
  url:imageUrl_(x&&x.url),name:str_(x&&x.name,90),
  width:Math.max(0,Number(x&&x.width)||0),
  height:Math.max(0,Number(x&&x.height)||0)
 })).filter(x=>x.url);
}
function offers_(){
 setupSafirMedia();
 const sh=sheet_(SAFIR.offersTab),last=sh.getLastRow();
 if(last<2)return [];
 return sh.getRange(2,1,last-1,12).getValues()
  .filter(r=>r[0]).map(r=>({
   id:String(r[0]),title:str_(r[1],120),price:Number(r[2])||0,
   departure_date:date_(r[3]),duration_days:Number(r[4])||0,
   hotel:str_(r[5],180),description:String(r[6]||''),
   status:str_(r[7],20)||'مسودة',updated_at:date_(r[8]),
   image_url:imageUrl_(r[9]),gallery:cleanGallery_(parseJson_(r[10],[])),
   extras:parseJson_(r[11],{})
  })).reverse();
}
function bookings_(){
 const sh=sheet_(SAFIR.bookingsTab),last=sh.getLastRow();
 if(last<2)return [];
 const from=Math.max(2,last-249);
 return sh.getRange(from,1,last-from+1,8).getValues()
 .filter(r=>r[0]).map(r=>({
  id:String(r[0]),created_at:date_(r[1]),name:str_(r[2],100),
  phone:str_(r[3],30),service:str_(r[4],50),
  travel_date:date_(r[5]),notes:str_(r[6],2000),
  status:str_(r[7],30)||'جديد'
 })).reverse();
}
function getDashboardData(){
 const offers=offers_(),bookings=bookings_();
 const b=sheet_(SAFIR.bookingsTab),last=b.getLastRow();
 const allStatuses=last>1?b.getRange(2,8,last-1,1).getValues():[];
 return {offers,bookings,totals:{
  offers:offers.length,active:offers.filter(x=>x.status==='منشور').length,
  drafts:offers.filter(x=>x.status==='مسودة').length,
  bookings:Math.max(0,last-1),
  newBookings:allStatuses.filter(r=>String(r[0]).trim()==='جديد').length
 }};
}
function findRow_(sh,id){
 const last=sh.getLastRow();if(last<2)return -1;
 const ids=sh.getRange(2,1,last-1,1).getValues();
 const i=ids.findIndex(r=>String(r[0])===id);return i<0?-1:i+2;
}
function saveOffer(data){
 if(!data||typeof data!=='object')throw Error('البيانات غير صحيحة.');
 const title=str_(data.title,120),price=Number(data.price),status=str_(data.status,20);
 if(title.length<4)throw Error('اكتب عنوانًا واضحًا للعرض.');
 if(!Number.isFinite(price)||price<0)throw Error('السعر غير صحيح.');
 if(!['مسودة','منشور','مخفي','منتهي'].includes(status))throw Error('حالة العرض غير صحيحة.');
 const date=str_(data.departure_date,10);
 if(date&&!/^\d{4}-\d{2}-\d{2}$/.test(date))throw Error('تاريخ السفر غير صحيح.');
 const duration=Number(data.duration_days)||0;
 if(duration<0||duration>365)throw Error('راجع مدة الرحلة.');
 const gallery=cleanGallery_(data.gallery);
 const image=imageUrl_(data.image_url);
 const extras={
  madinahHotel:str_(data.extras&&data.extras.madinahHotel,150),
  returnDate:str_(data.extras&&data.extras.returnDate,10),
  transport:str_(data.extras&&data.extras.transport,150),
  includes:str_(data.extras&&data.extras.includes,900),
  excludes:str_(data.extras&&data.extras.excludes,900),
  badge:str_(data.extras&&data.extras.badge,60)
 };
 const lock=LockService.getDocumentLock()||LockService.getScriptLock();
 lock.waitLock(30000);
 try{
  const sh=sheet_(SAFIR.offersTab);setupSafirMedia();
  const target=str_(data.id,100),row=target?findRow_(sh,target):-1;
  if(target&&row<0)throw Error('العرض المطلوب تعديله لم يعد موجودًا. حدّث اللوحة.');
  const id=row>0?target:Utilities.getUuid();
  const values=[id,plain_(title,120),price,date,duration,
    plain_(data.hotel,150),plain_(data.description,2000),status,new Date().toISOString(),
    image,JSON.stringify(gallery),JSON.stringify(extras)];
  if(row>0)sh.getRange(row,1,1,values.length).setValues([values]);
  else sh.appendRow(values);
  SpreadsheetApp.flush();
  return {ok:true,id,status};
 }finally{lock.releaseLock()}
}
function setBookingStatus(id,status){
 if(!['جديد','تم التواصل','مؤكد','ملغي'].includes(status))throw Error('حالة غير صحيحة.');
 const lock=LockService.getDocumentLock()||LockService.getScriptLock();
 lock.waitLock(15000);
 try{
  const sh=sheet_(SAFIR.bookingsTab),row=findRow_(sh,str_(id,120));
  if(row<0)throw Error('طلب الحجز غير موجود.');
  sh.getRange(row,8).setValue(status);
  return {ok:true};
 }finally{lock.releaseLock()}
}
function mediaFolder_(){
 const props=PropertiesService.getScriptProperties();
 const old=props.getProperty(SAFIR.mediaFolderProperty);
 if(old){try{return DriveApp.getFolderById(old)}catch(_){}}
 const folder=DriveApp.createFolder('SAFIR Al-Haramain - Website Images');
 props.setProperty(SAFIR.mediaFolderProperty,folder.getId());
 return folder;
}
function uploadOfferImage(input){
 if(!input||typeof input!=='object')throw Error('لم تصل الصورة.');
 const mime=str_(input.mime,40);
 if(!['image/webp','image/jpeg','image/png'].includes(mime))throw Error('نوع الصورة غير مدعوم.');
 const base64=String(input.base64||'');
 if(!base64||base64.length>6*1024*1024||!/^[A-Za-z0-9+/]*={0,2}$/.test(base64))throw Error('حجم الصورة كبير أو الملف غير صحيح.');
 const bytes=Utilities.base64Decode(base64);
 if(bytes.length>4*1024*1024)throw Error('الصورة أكبر من 4 ميجابايت بعد المعالجة.');
 const b=i=>(bytes[i]||0)&255;
 const png=b(0)===137&&b(1)===80&&b(2)===78&&b(3)===71;
 const jpg=b(0)===255&&b(1)===216&&b(2)===255;
 const webp=b(0)===82&&b(1)===73&&b(2)===70&&b(3)===70&&b(8)===87&&b(9)===69&&b(10)===66&&b(11)===80;
 if(!(mime==='image/png'&&png||mime==='image/jpeg'&&jpg||mime==='image/webp'&&webp))throw Error('توقيع الصورة غير صحيح.');
 const filename='umrah-'+Utilities.getUuid().slice(0,10)+'.'+(mime==='image/webp'?'webp':mime==='image/png'?'png':'jpg');
 const file=mediaFolder_().createFile(Utilities.newBlob(bytes,mime,filename));
 try{file.setSharing(DriveApp.Access.ANYONE_WITH_LINK,DriveApp.Permission.VIEW);}
 catch(err){file.setTrashed(true);throw Error('تعذرت مشاركة الصورة للعرض على الموقع: '+err.message);}
 const id=file.getId();
 return {ok:true,fileId:id,name:str_(input.name,90)||filename,
  url:'https://drive.google.com/thumbnail?id='+encodeURIComponent(id)+'&sz=w1600',
  width:Math.max(0,Number(input.width)||0),height:Math.max(0,Number(input.height)||0)};
}
