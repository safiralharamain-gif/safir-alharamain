/**
 * سفير الحرمين — عرض عروض العمرة المنشورة
 * يوضع في مشروع Apps Script العام للعروض فقط؛ لا تنشر مشروع الإدارة.
 * يقرأ تبويب عروض العمرة دون الوصول لبيانات العملاء.
 */
const SAFIR_PUBLIC_SHEET_ID='1da0GKq95dzyeTd-hr6ceSoGq5IekUge17Vm-eopJMNw';
function esc_(s){return String(s==null?'':s).replace(/[&<>"']/g,function(ch){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[ch]})}
function text_(v,n){return String(v==null?'':v).trim().slice(0,n||500)}
function url_(v){const u=text_(v,1000);return /^https:\/\/[^\s<>"']+$/i.test(u)?u:''}
function date_(v){return v instanceof Date?Utilities.formatDate(v,'Africa/Cairo','yyyy-MM-dd'):text_(v,30)}
function json_(v){try{return JSON.parse(String(v||'{}'))||{}}catch(_){return {}}}
function doGet(){
 const sh=SpreadsheetApp.openById(SAFIR_PUBLIC_SHEET_ID).getSheetByName('عروض العمرة');
 if(!sh)throw Error('تبويب العروض غير موجود');
 const last=sh.getLastRow(),rows=last>1?sh.getRange(2,1,last-1,12).getValues():[];
 const offers=rows.filter(r=>String(r[7]).trim()==='منشور').reverse();
 let list=offers.map(function(r){
  const title=text_(r[1],120),price=Number(r[2])||0,departure=date_(r[3]),duration=Number(r[4])||0;
  const hotel=text_(r[5],150),description=text_(r[6],1200),image=url_(r[9]);
  const extras=json_(r[11]),medinah=text_(extras.madinahHotel,150),badge=text_(extras.badge,55);
  const gallery=json_(r[10]);const imgs=Array.isArray(gallery)?gallery.slice(0,4):[];
  const photo=image?'<img loading="lazy" alt="'+esc_(title)+'" src="'+esc_(image)+'">':'<div class="blank">🕋</div>';
  const meta=[
    departure?'السفر: '+departure:'',
    duration?'المدة: '+duration+' يوم':'',
    hotel?'فندق مكة: '+hotel:'',
    medinah?'فندق المدينة: '+medinah:''
  ].filter(Boolean).map(x=>'<span>'+esc_(x)+'</span>').join('');
  const imgsHtml=imgs.length>1?'<div class="gallery">'+imgs.filter(x=>url_(x.url)&&url_(x.url)!==image).map(x=>'<img loading="lazy" src="'+esc_(url_(x.url))+'" alt="صورة إضافية للرحلة">').join('')+'</div>':'';
  const message='السلام عليكم، أريد تفاصيل '+title;
  return '<article class="trip"><div class="photo">'+photo+'</div><div class="info">'+(badge?'<span class="badge">'+esc_(badge)+'</span>':'')+
    '<h2>'+esc_(title)+'</h2><div class="meta">'+meta+'</div>'+
    (price?'<strong class="price">'+price.toLocaleString('en-US')+' جنيه</strong>':'<span class="price">السعر عند الاستفسار</span>')+
    (description?'<p class="description">'+esc_(description)+'</p>':'')+
    imgsHtml+
    '<a class="contact" href="https://wa.me/201150337383?text='+encodeURIComponent(message)+'" target="_blank" rel="noopener noreferrer">استفسر عن العرض عبر واتساب</a></div></article>';
 }).join('');
 const css=String.raw`
  *{box-sizing:border-box}body{margin:0;background:#fbfaf7;font-family:Tahoma,Arial,sans-serif;color:#23443a;padding:16px;direction:rtl}
  .list{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px;max-width:1200px;margin:auto}
  .trip{background:white;border:1px solid #e4e4dd;border-radius:17px;overflow:hidden;box-shadow:0 6px 24px #163d2910;min-width:0}
  .photo{height:255px;background:#f8f6f0;display:flex;justify-content:center;align-items:center}
  .photo img{width:100%;height:100%;object-fit:contain;object-position:center}.blank{font-size:55px}
  .info{padding:18px}.info h2{font-size:19px;line-height:1.6;margin:10px 0}
  .badge{background:#f4e7cb;border-radius:100px;padding:6px 11px;font-size:11px;color:#886423}
  .meta{display:flex;gap:8px;flex-wrap:wrap}.meta span{background:#f3f7f3;border-radius:7px;padding:6px 8px;font-size:12px}
  .price{display:block;font-size:21px;color:#166144;margin:15px 0}
  .description{font-size:13px;color:#5c7065;line-height:2;white-space:pre-line}
  .contact{display:inline-block;background:#165842;color:white;padding:12px 16px;text-decoration:none;border-radius:11px;margin-top:14px}
  .gallery{display:flex;gap:9px;overflow:auto;padding:5px 0}.gallery img{width:100px;height:80px;object-fit:contain;border:1px solid #e1e6df;border-radius:9px;background:#faf8f4;flex-shrink:0}
  .empty{text-align:center;border:1px dashed #ccdbc9;padding:35px 16px;border-radius:13px;color:#638070}
  @media(max-width:550px){body{padding:8px}.list{grid-template-columns:1fr}.photo{height:230px}}
 `;
 const body='<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'</style></head><body><main class="list">'+(list||'<div class="empty">لا توجد عروض عمرة منشورة حاليًا. تابعنا لمعرفة الرحلات الجديدة.</div>')+'</main></body></html>';
 return HtmlService.createHtmlOutput(body).setTitle('عروض العمرة | سفير الحرمين')
   .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}
