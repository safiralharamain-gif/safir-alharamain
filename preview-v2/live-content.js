
(()=>{
const DATA='preview-v2/data/site-content.json?v='+Date.now();
const e=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const wa=(txt)=>'https://wa.me/201150337383?text='+encodeURIComponent(txt);
function picture(src,title){
 if(!src || /^(?:javascript:|data:|file:)/i.test(String(src).trim()))return '';
 return '<div class="cover"><img loading="lazy" src="'+e(src)+'" alt="'+e(title||'صورة سفير الحرمين')+'"></div>';
}
function yt(url){
 try{const u=new URL(url),h=u.hostname;let id='';if(h.includes('youtu.be'))id=u.pathname.slice(1);else id=u.searchParams.get('v')||((u.pathname.match(/\/(?:shorts|embed)\/([^/?]+)/)||[])[1]||'');return id?'https://www.youtube.com/embed/'+id:''}catch(_){return''}
}
function section(title,body,alt=false,note=''){
 const s=document.createElement('section');s.className='section safir-preview-content'+(alt?' alt':'');
 s.innerHTML='<div class="container text-center"><h2 class="head-center position-relative mb-4">'+e(title)+'</h2>'+(note?'<p class="safir-preview-section-note">'+e(note)+'</p>':'')+body+'</div>';
 return s;
}
function cardProgram(x){
 const img=x.image||'img/umrah-trips.png';
 return '<article class="safir-preview-card text-start">'+picture(img,x.title||'برنامج عمرة')+'<div class="body"><span class="safir-preview-badge">'+e(x.status||'متاح')+'</span><h3>'+e(x.title||'برنامج عمرة')+'</h3><div class="safir-preview-meta">'+
 (x.date?'<span>'+e(x.date)+'</span>':'')+(x.duration?'<span>'+e(x.duration)+'</span>':'')+(x.makkahHotel?'<span>مكة: '+e(x.makkahHotel)+'</span>':'')+(x.madinahHotel?'<span>المدينة: '+e(x.madinahHotel)+'</span>':'')+(x.price?'<span>السعر: '+e(x.price)+'</span>':'')+
 '</div>'+(x.summary?'<p>'+e(x.summary)+'</p>':'')+'<div class="safir-preview-actions"><a class="btn btn-secondary rounded-5 px-4" target="_blank" href="'+wa('السلام عليكم، أريد الاستفسار عن '+(x.title||'برنامج العمرة'))+'">استفسر على واتساب</a></div></div></article>';
}
function render(data){
 const car=document.querySelector('#carouselIndicators');
 if(data.home?.announcement){
   const a=document.createElement('div');a.className='safir-preview-announcement';a.textContent=data.home.announcement;
   car?car.insertAdjacentElement('afterend',a):document.body.prepend(a);
 }
 const anchor=document.querySelector('.adds')||document.querySelector('.services');
 if(!anchor)return;
 const insert=(node)=>anchor.parentNode.insertBefore(node,anchor);

 // Umrah offers are managed exclusively in the owner Google Sheet.
 // Do not display legacy GitHub preview programs/offers as if they were live.
 insert(section('برامج العمرة',
   '<div class="safir-preview-empty">'+
   '<p>اعرف أحدث برامج العمرة المنشورة وأسعارها وفنادقها من صفحة البرامج المتصلة مباشرة بلوحة التحكم.</p>'+
   '<a href="umrah-programs.html" class="btn btn-secondary rounded-5 px-4">عرض برامج العمرة الحالية</a>'+
   '</div>',
   false,'الصفحة تعرض العروض التي تختار لها الإدارة حالة «منشور» فقط.'));

 const gifts=(data.gifts||[]).filter(x=>x.visible!==false);
 if(gifts.length) insert(section('هدايا وجوائز العمرة','<div class="safir-preview-grid">'+gifts.map(x=>'<article class="safir-preview-card text-start">'+picture(x.image,x.title||'هدية')+'<div class="body"><span class="safir-preview-badge">'+e(x.status||'مسابقة')+'</span><h3>'+e(x.title||'هدية')+'</h3>'+(x.prize?'<h4 class="text-secondary">'+e(x.prize)+'</h4>':'')+(x.conditions?'<p>'+e(x.conditions)+'</p>':'')+(x.winner?'<p><b>الفائز:</b> '+e(x.winner)+'</p>':'')+'</div></article>').join('')+'</div>',false));

 const videos=(data.videos||[]).filter(x=>x.visible!==false);
 if(videos.length) insert(section('فيديوهات سفير الحرمين','<div class="safir-preview-grid">'+videos.map(x=>{const y=yt(x.url);return '<article class="safir-preview-card text-start">'+(y?'<iframe class="safir-preview-video" loading="lazy" src="'+e(y)+'" allowfullscreen></iframe>':'')+'<div class="body"><h3>'+e(x.title||'فيديو')+'</h3>'+(x.description?'<p>'+e(x.description)+'</p>':'')+'</div></article>'}).join('')+'</div>',true));

 const past=(data.pastTrips||[]).filter(x=>x.visible!==false);
 if(past.length) insert(section('رحلاتنا السابقة','<div class="safir-preview-grid">'+past.map(x=>'<article class="safir-preview-card text-start">'+picture(x.cover||'img/umrah-trips.png',x.title||'رحلة سابقة')+'<div class="body"><h3>'+e(x.title||'رحلة سابقة')+'</h3>'+(x.date?'<div class="safir-preview-meta"><span>'+e(x.date)+'</span></div>':'')+(x.description?'<p>'+e(x.description)+'</p>':'')+'</div></article>').join('')+'</div>',false));

 const hajj=(data.hajjPrograms||[]).filter(x=>x.visible!==false);
 if(hajj.length) insert(section('برامج الحج','<div class="safir-preview-grid">'+hajj.map(x=>'<article class="safir-preview-card text-start">'+picture(x.image,x.title||'برنامج حج')+'<div class="body"><span class="safir-preview-badge">'+e(x.status||'متاح')+'</span><h3>'+e(x.title||'برنامج حج')+'</h3><div class="safir-preview-meta">'+(x.type?'<span>'+e(x.type)+'</span>':'')+(x.price?'<span>السعر: '+e(x.price)+'</span>':'')+(x.bookingAmount?'<span>جدية الحجز: '+e(x.bookingAmount)+'</span>':'')+'</div>'+(x.details?'<p>'+e(x.details)+'</p>':'')+'</div></article>').join('')+'</div>',true));

 const faq=(data.faq||[]).filter(x=>x.visible!==false);
 if(faq.length) insert(section('الأسئلة الشائعة','<div class="safir-preview-faq text-start">'+faq.map(x=>'<details><summary>'+e(x.question||'سؤال')+'</summary><p class="mt-3 mb-0">'+e(x.answer||'')+'</p></details>').join('')+'</div>',false));
}
fetch(DATA,{cache:'no-store'}).then(r=>r.json()).then(render).catch(err=>console.error('Preview CMS load failed',err));
})();
