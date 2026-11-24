/* سفير الحرمين — برنامج العمرة: بطاقات بنفس تصميم الموقع مع نسخة احتياطية من العروض المنشورة */
(function(){
'use strict';
var root=document.getElementById('safir-umrah-root');if(!root)return;
var BACKUP='data/umrah-programs-published.json';
var API='https://script.google.com/macros/s/AKfycbz85MU5YkKwBIcC2d5pH0OaJqptfEOKIo9TSaYAzlUJ9eBg1g23AvCB7-liR-OEUArk/exec';
var state={live:false,latest:[]};
function element(name,className,text){
 var e=document.createElement(name);if(className)e.className=className;if(text!==undefined)e.textContent=String(text);return e;
}
function validUrl(x){return /^https:\/\/[^\s"'<>]+$/i.test(String(x||''))?String(x):''}
function addLine(parent,key,value){
 if(!value)return;
 var row=element('div'),bold=element('b','',key),text=element('span','',value);row.append(bold,text);parent.append(row);
}
function image(src,alt){
 var box=element('div','safir-umrah-picture'),link=validUrl(src);
 if(!link){box.append(element('div','safir-image-empty','صورة برنامج العمرة'));return box}
 var img=element('img');img.alt=alt||'صورة العرض';img.loading='lazy';img.decoding='async';img.src=link;
 img.onerror=function(){img.remove();box.append(element('div','safir-image-empty','تعذر عرض الصورة على هذا الجهاز'))};
 box.append(img);return box;
}
function makeCard(o){
 var article=element('article','safir-umrah-card');
 var title=String(o.title||'برنامج عمرة'),extras=o.extras&&typeof o.extras==='object'?o.extras:{};
 article.append(image(o.image_url,title));
 var body=element('div','safir-umrah-body');
 if(extras.badge)body.append(element('span','safir-umrah-tag',extras.badge));
 body.append(element('h3','',title));
 var price=Number(o.price);
 if(Number.isFinite(price)&&price>0){
  var p=element('div','safir-umrah-price',price.toLocaleString('ar-EG')+' جنيه');
  body.append(p);
 }else body.append(element('div','safir-umrah-price','السعر عند الاستفسار'));
 var details=element('div','safir-umrah-details');
 addLine(details,'تاريخ السفر:',o.departure_date||'يُحدد لاحقًا');
 if(Number(o.duration_days)>0)addLine(details,'المدة:',o.duration_days+' يوم');
 addLine(details,'فندق مكة:',o.hotel);
 addLine(details,'فندق المدينة:',extras.madinahHotel);
 addLine(details,'تاريخ العودة:',extras.returnDate);
 addLine(details,'الانتقالات:',extras.transport);
 body.append(details);
 if(o.description)body.append(element('p','safir-umrah-description',o.description));
 if(o.gallery&&Array.isArray(o.gallery)){
  var gallery=element('div','safir-umrah-gallery');
  o.gallery.slice(0,12).forEach(function(g){
   var u=validUrl(g&&g.url);
   if(!u||u===o.image_url)return;
   var img=element('img');img.src=u;img.loading='lazy';img.alt='صورة إضافية من '+title;gallery.append(img);
  });
  if(gallery.childNodes.length)body.append(gallery);
 }
 var actions=element('div','safir-umrah-actions');
 var a=element('a','safir-umrah-action','استفسر عن البرنامج');
 a.href='https://wa.me/201150337383?text='+encodeURIComponent('السلام عليكم، أريد الاستفسار عن برنامج: '+title);
 a.target='_blank';a.rel='noopener noreferrer';
 actions.append(a);body.append(actions);
 article.append(body);return article;
}
function render(data,source){
 var offers=Array.isArray(data)?data:Array.isArray(data&&data.offers)?data.offers:[];
 offers=offers.filter(function(o){return o&&o.status==='منشور'&&o.title});
 state.latest=offers;
 root.replaceChildren();
 if(!offers.length){root.append(element('div','safir-umrah-alert','لا توجد برامج عمرة منشورة حاليًا. تابعنا لمعرفة البرامج الجديدة.'));return}
 var grid=element('div','safir-umrah-grid');offers.forEach(function(o){grid.append(makeCard(o))});
 root.append(grid);
 var msg=source==='live'?'العروض محدثة مباشرة من لوحة التحكم.':'العروض المعروضة هي آخر نسخة منشورة تم التحقق منها. التحديث المباشر يحتاج تفعيل خدمة مزامنة العروض.';
 root.append(element('p','safir-umrah-source',msg));
}
function loadBackup(){
 fetch(BACKUP,{cache:'no-store'}).then(function(r){if(!r.ok)throw Error('snapshot');return r.json()})
 .then(function(data){if(!state.live)render(data,'snapshot')})
 .catch(function(){if(!state.live)root.replaceChildren(element('div','safir-umrah-alert','تعذر تحميل عروض العمرة مؤقتًا. للاستفسار اتصل بنا على 01150337383.'))});
}
window.safirUmrahReceive=function(payload){
 if(!payload||payload.ok!==true||!Array.isArray(payload.offers))return;
 state.live=true;render(payload,'live');
};
function loadLive(){
 var tag=document.createElement('script');tag.async=true;
 tag.src=API+'?format=jsonp&callback=safirUmrahReceive&t='+Date.now();
 tag.onerror=function(){tag.remove()};
 document.head.append(tag);
}
loadBackup();
loadLive();
})();
