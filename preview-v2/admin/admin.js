(()=>{
const DATA_URL='../data/site-content.json?v='+Date.now();
const DRAFT_KEY='safirPreviewV2AdminDraft';
const REQUEST_BASE='https://github.com/safiralharamain-gif/safir-alharamain/new/main/preview-v2/cms-requests';
let data={};

const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const lines=s=>String(s||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
const join=a=>(Array.isArray(a)?a:[]).join('\n');
function toast(t){const e=$('#status');e.textContent=t;e.style.display='block';clearTimeout(window.__st);window.__st=setTimeout(()=>e.style.display='none',2400)}
function blank(type){
 const map={
  umrahPrograms:{title:'برنامج عمرة جديد',date:'',duration:'',makkahHotel:'',madinahHotel:'',price:'',status:'متاح',image:'',summary:'',featured:false,visible:true},
  pastTrips:{title:'رحلة سابقة جديدة',date:'',description:'',cover:'',images:[],videos:[],visible:true},
  videos:{title:'فيديو جديد',url:'',category:'عمرة',description:'',visible:true},
  offers:{title:'عرض جديد',badge:'عرض',details:'',price:'',startDate:'',endDate:'',image:'',visible:true},
  gifts:{title:'هدية / مسابقة جديدة',prize:'',conditions:'',endDate:'',status:'مفتوحة',winner:'',image:'',visible:true},
  hajjPrograms:{title:'برنامج حج جديد',type:'',price:'',bookingAmount:'',details:'',status:'متاح',image:'',visible:true},
  faq:{question:'سؤال جديد',answer:'',category:'عام',visible:true}
 }; return structuredClone(map[type]);
}
function loadDraft(){try{return JSON.parse(localStorage.getItem(DRAFT_KEY)||'null')}catch(e){return null}}
function saveDraft(){collect();localStorage.setItem(DRAFT_KEY,JSON.stringify(data));renderStats();toast('تم حفظ المسودة تلقائيًا')}
function field(label,name,val='',type='text',extra=''){return '<div class="field"><label>'+label+'</label><input '+extra+' data-f="'+name+'" type="'+type+'" value="'+esc(val)+'"></div>'}
function textarea(label,name,val=''){return '<div class="field"><label>'+label+'</label><textarea data-f="'+name+'">'+esc(val)+'</textarea></div>'}
function editorShell(type,item,i,body){return '<div class="editor" data-type="'+type+'" data-index="'+i+'"><div class="editor-title"><h3>'+esc(item.title||item.question||('عنصر '+(i+1)))+'</h3><div><button class="btn outline small" data-toggle>'+((item.visible===false)?'إظهار':'إخفاء')+'</button> <button class="btn danger small" data-delete>حذف</button></div></div><div class="mt">'+body+'</div></div>'}
function renderList(type){
 const list=$('#'+type+'List'), arr=data[type]||[]; if(!list)return;
 if(!arr.length){list.innerHTML='<div class="empty">لا توجد عناصر. اضغط «إضافة» للبدء.</div>';return}
 list.innerHTML=arr.map((x,i)=>{
   let b='';
   if(type==='umrahPrograms') b='<div class="grid3">'+field('اسم البرنامج','title',x.title)+field('التاريخ','date',x.date)+field('المدة','duration',x.duration)+field('فندق مكة','makkahHotel',x.makkahHotel)+field('فندق المدينة','madinahHotel',x.madinahHotel)+field('السعر المعتمد','price',x.price)+field('الحالة','status',x.status)+field('مسار/رابط الصورة','image',x.image)+'</div><div class="mt">'+textarea('وصف مختصر','summary',x.summary)+'</div><label class="check mt"><input data-f="featured" type="checkbox" '+(x.featured?'checked':'')+'> إظهار كمميز في الرئيسية</label>';
   if(type==='pastTrips') b='<div class="grid3">'+field('اسم الرحلة','title',x.title)+field('التاريخ','date',x.date)+field('صورة الغلاف','cover',x.cover)+'</div><div class="mt">'+textarea('وصف الرحلة','description',x.description)+'</div><div class="grid2 mt">'+textarea('صور الرحلة — كل سطر صورة','images',join(x.images))+textarea('فيديوهات YouTube — كل سطر رابط','videos',join(x.videos))+'</div>';
   if(type==='videos') b='<div class="grid3">'+field('العنوان','title',x.title)+field('رابط YouTube','url',x.url)+field('التصنيف','category',x.category)+'</div><div class="mt">'+textarea('وصف مختصر','description',x.description)+'</div>';
   if(type==='offers') b='<div class="grid3">'+field('عنوان العرض','title',x.title)+field('وسم العرض','badge',x.badge)+field('السعر/الميزة','price',x.price)+field('تاريخ البداية','startDate',x.startDate)+field('تاريخ النهاية','endDate',x.endDate)+field('مسار/رابط الصورة','image',x.image)+'</div><div class="mt">'+textarea('تفاصيل العرض','details',x.details)+'</div>';
   if(type==='gifts') b='<div class="grid3">'+field('اسم المسابقة/الهدية','title',x.title)+field('الجائزة','prize',x.prize)+field('الحالة','status',x.status)+field('آخر موعد','endDate',x.endDate)+field('اسم الفائز','winner',x.winner)+field('مسار/رابط الصورة','image',x.image)+'</div><div class="mt">'+textarea('الشروط','conditions',x.conditions)+'</div>';
   if(type==='hajjPrograms') b='<div class="grid3">'+field('اسم البرنامج','title',x.title)+field('النوع/المستوى','type',x.type)+field('السعر المعتمد','price',x.price)+field('جدية الحجز','bookingAmount',x.bookingAmount)+field('الحالة','status',x.status)+field('مسار/رابط الصورة','image',x.image)+'</div><div class="mt">'+textarea('تفاصيل البرنامج','details',x.details)+'</div>';
   if(type==='faq') b='<div class="grid2">'+field('السؤال','question',x.question)+field('التصنيف','category',x.category)+'</div><div class="mt">'+textarea('الإجابة','answer',x.answer)+'</div>';
   return editorShell(type,x,i,b);
 }).join('');
 bindEditors();
}
function bindEditors(){
 $$('.editor input,.editor textarea,.editor select').forEach(el=>{el.oninput=saveDraft;el.onchange=saveDraft});
 $$('[data-delete]').forEach(btn=>btn.onclick=()=>{const e=btn.closest('.editor'),type=e.dataset.type,i=+e.dataset.index;if(confirm('حذف العنصر؟')){data[type].splice(i,1);renderList(type);saveDraft()}});
 $$('[data-toggle]').forEach(btn=>btn.onclick=()=>{const e=btn.closest('.editor'),type=e.dataset.type,i=+e.dataset.index;data[type][i].visible=data[type][i].visible===false?true:false;renderList(type);saveDraft()});
}
function collect(){
 data.brand=data.brand||{};data.home=data.home||{};
 data.brand.eyebrow=$('#brandEyebrow')?.value.trim()||'';
 data.brand.title=$('#brandTitle')?.value.trim()||'';
 data.brand.intro=$('#brandIntro')?.value.trim()||'';
 data.home.announcement=$('#homeAnnouncement')?.value.trim()||'';
 data.home.heroNote=$('#homeHeroNote')?.value.trim()||'';
 data.umrahGuide={
   title:$('#umrahGuideTitle')?.value.trim()||'',
   subtitle:$('#umrahGuideSubtitle')?.value.trim()||'',
   body:$('#umrahGuideBody')?.value.trim()||'',
   images:lines($('#umrahGuideImages')?.value||''),
   videos:lines($('#umrahGuideVideos')?.value||'')
 };
 $$('.editor').forEach(e=>{const type=e.dataset.type,i=+e.dataset.index,obj=data[type][i];e.querySelectorAll('[data-f]').forEach(el=>{const k=el.dataset.f;if(k==='images'||k==='videos')obj[k]=lines(el.value);else if(el.type==='checkbox')obj[k]=el.checked;else obj[k]=el.value.trim()})});
 return data;
}
function fillStatic(){
 const b=data.brand||{},h=data.home||{},u=data.umrahGuide||{};
 $('#brandEyebrow').value=b.eyebrow||'';$('#brandTitle').value=b.title||'';$('#brandIntro').value=b.intro||'';
 $('#homeAnnouncement').value=h.announcement||'';$('#homeHeroNote').value=h.heroNote||'';
 $('#umrahGuideTitle').value=u.title||'';$('#umrahGuideSubtitle').value=u.subtitle||'';$('#umrahGuideBody').value=u.body||'';$('#umrahGuideImages').value=join(u.images);$('#umrahGuideVideos').value=join(u.videos);
 ['#brandEyebrow','#brandTitle','#brandIntro','#homeAnnouncement','#homeHeroNote','#umrahGuideTitle','#umrahGuideSubtitle','#umrahGuideBody','#umrahGuideImages','#umrahGuideVideos'].forEach(s=>$(s).oninput=saveDraft);
}
function renderAll(){['umrahPrograms','pastTrips','videos','offers','gifts','hajjPrograms','faq'].forEach(renderList);fillStatic();renderStats()}
function renderStats(){const c=t=>(data[t]||[]).filter(x=>x.visible!==false).length;$('#sUmrah').textContent=c('umrahPrograms');$('#sPast').textContent=c('pastTrips');$('#sVideos').textContent=c('videos');$('#sOffers').textContent=c('offers')+c('gifts')}
function publish(){
 collect();localStorage.setItem(DRAFT_KEY,JSON.stringify(data));
 const payload=JSON.stringify(data,null,2),filename='request-'+Date.now()+'.json';
 const url=REQUEST_BASE+'?filename='+encodeURIComponent(filename)+'&value='+encodeURIComponent(payload);
 toast('تم تجهيز ملف النشر. افتح GitHub واضغط Commit changes فقط.');
 window.open(url,'_blank');
}
function exportData(){collect();const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='safir-preview-v2-backup.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
function importData(file){const r=new FileReader();r.onload=()=>{try{data=JSON.parse(r.result);localStorage.setItem(DRAFT_KEY,JSON.stringify(data));renderAll();toast('تم استيراد النسخة بنجاح')}catch(e){alert('ملف JSON غير صالح')}};r.readAsText(file)}
$$('.navbtn').forEach(b=>b.onclick=()=>{$$('.navbtn').forEach(x=>x.classList.remove('active'));b.classList.add('active');$$('.panel').forEach(x=>x.classList.remove('active'));$('#'+b.dataset.panel).classList.add('active');$('#pageTitle').textContent=b.textContent.trim();if(innerWidth<981)$('#side').classList.remove('open')});
$$('[data-add]').forEach(b=>b.onclick=()=>{const t=b.dataset.add;data[t]=data[t]||[];data[t].push(blank(t));renderList(t);saveDraft()});
$('#publishBtn').onclick=publish;$('#exportBtn').onclick=exportData;$('#importFile').onchange=e=>e.target.files[0]&&importData(e.target.files[0]);$('#menuToggle').onclick=()=>$('#side').classList.toggle('open');
const draft=loadDraft();
fetch(DATA_URL,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()).then(remote=>{data=draft||remote||{};renderAll();toast(draft?'تم استرجاع المسودة':'تم تحميل بيانات نسخة المعاينة')}).catch(()=>{data=draft||{};renderAll();toast('تم فتح المسودة المحلية')});
})();