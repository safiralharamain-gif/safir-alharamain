(() => {
const OWNER='safiralharamain-gif', REPO='safir-alharamain', BRANCH='main', DATA_PATH='data/site-content.json';
let contentSha='', data=null;
const $=id=>document.getElementById(id);
const lines=s=>String(s||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
const join=a=>(Array.isArray(a)?a:[]).join('\n');
const status=(msg,type='ok')=>{const el=$('status');el.textContent=msg;el.className='status show '+type};
const token=()=> $('githubToken').value.trim() || sessionStorage.getItem('safirGithubToken') || '';
function headers(){return {'Accept':'application/vnd.github+json','Authorization':'Bearer '+token(),'X-GitHub-Api-Version':'2022-11-28'}}

function b64FromUtf8(str){const bytes=new TextEncoder().encode(str);let bin='';const chunk=0x8000;for(let i=0;i<bytes.length;i+=chunk){bin+=String.fromCharCode(...bytes.subarray(i,i+chunk))}return btoa(bin)}
function utf8FromB64(b64){const bin=atob(b64.replace(/\n/g,''));const bytes=Uint8Array.from(bin,c=>c.charCodeAt(0));return new TextDecoder().decode(bytes)}
function fileB64(file){return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>{const s=String(r.result);resolve(s.split(',')[1])};r.onerror=reject;r.readAsDataURL(file)})}
function safeName(name){return name.normalize('NFKD').replace(/[^a-zA-Z0-9._-]+/g,'-').replace(/-+/g,'-').replace(/^-|-$/g,'') || 'image.jpg'}

async function api(url,opt={}){const res=await fetch(url,{...opt,headers:{...headers(),...(opt.headers||{})}});if(!res.ok){let t='';try{t=await res.text()}catch{}throw new Error('GitHub '+res.status+' '+t.slice(0,220))}return res.json()}

async function load(){
  if(!$('githubToken').value.trim() && sessionStorage.getItem('safirGithubToken')) $('githubToken').value=sessionStorage.getItem('safirGithubToken');
  if(!token()) return status('أدخل مفتاح GitHub أولاً.','err');
  sessionStorage.setItem('safirGithubToken',token());
  status('جاري الاتصال وتحميل البيانات...','ok');
  try{
    const f=await api('https://api.github.com/repos/'+OWNER+'/'+REPO+'/contents/'+DATA_PATH+'?ref='+BRANCH);
    contentSha=f.sha;
    data=JSON.parse(utf8FromB64(f.content));
    fill();
    status('تم الاتصال وتحميل بيانات الموقع بنجاح.','ok');
  }catch(e){status('تعذر الاتصال: '+e.message,'err')}
}

function fill(){
  const u=data.umrahGuide||{}, h=data.hajjGuide||{};
  $('umrahTitle').value=u.title||'';$('umrahSubtitle').value=u.subtitle||'';$('umrahBody').value=u.body||'';$('umrahImages').value=join(u.images);$('umrahVideos').value=join(u.videos);
  $('hajjTitle').value=h.title||'';$('hajjSubtitle').value=h.subtitle||'';$('hajjBody').value=h.body||'';$('hajjImages').value=join(h.images);$('hajjVideos').value=join(h.videos);
  renderTrips();
}

function collect(){
  data=data||{};
  data.umrahGuide={title:$('umrahTitle').value.trim(),subtitle:$('umrahSubtitle').value.trim(),body:$('umrahBody').value.trim(),images:lines($('umrahImages').value),videos:lines($('umrahVideos').value)};
  data.hajjGuide={title:$('hajjTitle').value.trim(),subtitle:$('hajjSubtitle').value.trim(),body:$('hajjBody').value.trim(),images:lines($('hajjImages').value),videos:lines($('hajjVideos').value)};
  data.pastTrips=[...document.querySelectorAll('.trip-editor')].map(el=>({
    title:el.querySelector('[data-f=title]').value.trim(),
    date:el.querySelector('[data-f=date]').value.trim(),
    description:el.querySelector('[data-f=description]').value.trim(),
    cover:el.querySelector('[data-f=cover]').value.trim(),
    images:lines(el.querySelector('[data-f=images]').value),
    videos:lines(el.querySelector('[data-f=videos]').value),
    visible:el.querySelector('[data-f=visible]').checked
  }));
}

function tripTemplate(t={},idx=0){
  return '<div class="trip-editor" data-index="'+idx+'">'+
    '<div class="trip-head"><h3>'+(t.title||('رحلة '+(idx+1)))+'</h3><button class="btn btn-danger" data-delete-trip>حذف الرحلة</button></div>'+
    '<div class="grid3" style="margin-top:14px">'+
      '<div><label>اسم الرحلة</label><input data-f="title" value="'+escAttr(t.title||'')+'"></div>'+
      '<div><label>التاريخ</label><input data-f="date" value="'+escAttr(t.date||'')+'" placeholder="مثال: 2-9-2026"></div>'+
      '<div><label>صورة الغلاف</label><input data-f="cover" value="'+escAttr(t.cover||'')+'"></div>'+
    '</div>'+
    '<div style="margin-top:14px"><label>وصف الرحلة</label><textarea data-f="description">'+escText(t.description||'')+'</textarea></div>'+
    '<div class="grid2" style="margin-top:14px">'+
      '<div><label>صور الرحلة — رابط في كل سطر</label><textarea data-f="images">'+escText(join(t.images))+'</textarea><div class="upload-line"><input type="file" accept="image/*" multiple data-trip-files><button class="btn btn-light" data-trip-upload>رفع صور الرحلة</button></div></div>'+
      '<div><label>فيديوهات YouTube — رابط في كل سطر</label><textarea data-f="videos">'+escText(join(t.videos))+'</textarea></div>'+
    '</div>'+
    '<div style="margin-top:12px"><label style="display:flex;gap:8px;align-items:center;font-weight:400"><input data-f="visible" type="checkbox" style="width:auto" '+(t.visible===false?'':'checked')+'> إظهار الرحلة في الموقع</label></div>'+
  '</div>';
}
function escAttr(s){return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;')}
function escText(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}

function renderTrips(){
  $('tripEditors').innerHTML=(data.pastTrips||[]).map(tripTemplate).join('');
  bindTripActions();
}
function bindTripActions(){
  document.querySelectorAll('[data-delete-trip]').forEach(b=>b.onclick=()=>{b.closest('.trip-editor').remove()});
  document.querySelectorAll('[data-trip-upload]').forEach(b=>b.onclick=async()=>{const ed=b.closest('.trip-editor'),input=ed.querySelector('[data-trip-files]'),out=ed.querySelector('[data-f=images]');await uploadFiles(input.files,out)});
}

async function uploadFiles(files,targetTextarea){
  if(!token()) return status('أدخل مفتاح GitHub أولاً.','err');
  if(!files || !files.length) return status('اختر صورة أو أكثر أولاً.','err');
  status('جاري رفع الصور...','ok');
  try{
    const added=[];
    for(const file of files){
      const path='img/content/'+Date.now()+'-'+safeName(file.name);
      const body={message:'Upload site content image: '+file.name,content:await fileB64(file),branch:BRANCH};
      await api('https://api.github.com/repos/'+OWNER+'/'+REPO+'/contents/'+path,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      added.push('./'+path);
      await new Promise(r=>setTimeout(r,40));
    }
    targetTextarea.value=[...lines(targetTextarea.value),...added].join('\n');
    status('تم رفع '+added.length+' صورة وإضافتها للقسم. اضغط حفظ ونشر التعديلات لحفظ بيانات الصفحة.','ok');
  }catch(e){status('فشل رفع الصور: '+e.message,'err')}
}

async function save(){
  if(!data) return status('اضغط اتصال وتحميل البيانات أولاً.','err');
  collect();
  status('جاري حفظ التعديلات على GitHub...','ok');
  try{
    const body={message:'Update Umrah portal content from admin panel',content:b64FromUtf8(JSON.stringify(data,null,2)),sha:contentSha,branch:BRANCH};
    const out=await api('https://api.github.com/repos/'+OWNER+'/'+REPO+'/contents/'+DATA_PATH,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    contentSha=out.content.sha;
    status('تم الحفظ بنجاح. التعديلات نُشرت في GitHub وستظهر على الموقع بعد تحديث GitHub Pages.','ok');
  }catch(e){status('فشل الحفظ: '+e.message,'err')}
}

$('connectBtn').onclick=load;
$('saveAll').onclick=save;$('saveAllBottom').onclick=save;
$('addTrip').onclick=()=>{data=data||{pastTrips:[]};collect();data.pastTrips=data.pastTrips||[];data.pastTrips.push({title:'رحلة جديدة',date:'',description:'',cover:'',images:[],videos:[],visible:true});renderTrips()};
document.querySelector('[data-upload=umrah]').onclick=()=>uploadFiles($('umrahUpload').files,$('umrahImages'));
document.querySelector('[data-upload=hajj]').onclick=()=>uploadFiles($('hajjUpload').files,$('hajjImages'));
if(sessionStorage.getItem('safirGithubToken')){$('githubToken').value=sessionStorage.getItem('safirGithubToken')}
})();