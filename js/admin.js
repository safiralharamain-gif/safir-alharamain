(() => {
  const DATA_URL='./data/site-content.json?v='+Date.now();
  const NEW_FILE_BASE='https://github.com/safiralharamain-gif/safir-alharamain/new/main/cms-requests';
  const DRAFT_KEY='safirCmsDraftV2';
  let data={};

  const $=id=>document.getElementById(id);
  const lines=s=>String(s||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
  const join=a=>(Array.isArray(a)?a:[]).join('\n');
  const escAttr=s=>String(s||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');
  const escText=s=>String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const setStatus=t=>{$('status').textContent=t};

  function fill(){
    const u=data.umrahGuide||{}, h=data.hajjGuide||{};
    $('umrahTitle').value=u.title||'';
    $('umrahSubtitle').value=u.subtitle||'';
    $('umrahBody').value=u.body||'';
    $('umrahImages').value=join(u.images);
    $('umrahVideos').value=join(u.videos);

    $('hajjTitle').value=h.title||'';
    $('hajjSubtitle').value=h.subtitle||'';
    $('hajjBody').value=h.body||'';
    $('hajjImages').value=join(h.images);
    $('hajjVideos').value=join(h.videos);
    renderTrips();
  }

  function collect(){
    data=data||{};
    data.brand=data.brand||{};
    data.umrahGuide={
      title:$('umrahTitle').value.trim(),
      subtitle:$('umrahSubtitle').value.trim(),
      body:$('umrahBody').value.trim(),
      images:lines($('umrahImages').value),
      videos:lines($('umrahVideos').value)
    };
    data.hajjGuide={
      title:$('hajjTitle').value.trim(),
      subtitle:$('hajjSubtitle').value.trim(),
      body:$('hajjBody').value.trim(),
      images:lines($('hajjImages').value),
      videos:lines($('hajjVideos').value)
    };
    data.pastTrips=[...document.querySelectorAll('.trip-editor')].map(el=>({
      title:el.querySelector('[data-f=title]').value.trim(),
      date:el.querySelector('[data-f=date]').value.trim(),
      description:el.querySelector('[data-f=description]').value.trim(),
      cover:el.querySelector('[data-f=cover]').value.trim(),
      images:lines(el.querySelector('[data-f=images]').value),
      videos:lines(el.querySelector('[data-f=videos]').value),
      visible:el.querySelector('[data-f=visible]').checked
    }));
    return data;
  }

  function saveDraft(){
    try{
      collect();
      localStorage.setItem(DRAFT_KEY, JSON.stringify({updatedAt:Date.now(),data}));
      setStatus('المسودة محفوظة تلقائيًا على الجهاز.');
    }catch(e){}
  }

  function loadDraft(){
    try{
      const raw=localStorage.getItem(DRAFT_KEY);
      if(!raw) return null;
      const d=JSON.parse(raw);
      if(!d || !d.data) return null;
      return d.data;
    }catch(e){return null}
  }

  function tripTemplate(t={},idx=0){
    return '<div class="trip-editor">'+
      '<div class="trip-head"><h3>'+(escText(t.title||('رحلة '+(idx+1))))+'</h3><button class="btn btn-danger" data-delete-trip>حذف</button></div>'+
      '<div class="grid3 mt">'+
        '<div><label>اسم الرحلة</label><input data-f="title" value="'+escAttr(t.title||'')+'"></div>'+
        '<div><label>التاريخ</label><input data-f="date" value="'+escAttr(t.date||'')+'" placeholder="مثال: 2-9-2026"></div>'+
        '<div><label>صورة الغلاف</label><input data-f="cover" value="'+escAttr(t.cover||'')+'" placeholder="./img/content/photo.jpg"></div>'+
      '</div>'+
      '<div class="mt"><label>وصف الرحلة</label><textarea data-f="description">'+escText(t.description||'')+'</textarea></div>'+
      '<div class="grid2 mt">'+
        '<div><label>صور الرحلة — صورة في كل سطر</label><textarea data-f="images">'+escText(join(t.images))+'</textarea></div>'+
        '<div><label>فيديوهات YouTube — رابط في كل سطر</label><textarea data-f="videos">'+escText(join(t.videos))+'</textarea></div>'+
      '</div>'+
      '<label class="check mt"><input data-f="visible" type="checkbox" '+(t.visible===false?'':'checked')+'> إظهار الرحلة في الموقع</label>'+
    '</div>';
  }

  function renderTrips(){
    $('tripEditors').innerHTML=(data.pastTrips||[]).map(tripTemplate).join('');
    document.querySelectorAll('[data-delete-trip]').forEach(btn=>{
      btn.onclick=()=>{btn.closest('.trip-editor').remove();saveDraft();};
    });
    bindAutosave();
  }

  function bindAutosave(){
    document.querySelectorAll('input,textarea').forEach(el=>{
      el.removeEventListener('input',saveDraft);
      el.removeEventListener('change',saveDraft);
      el.addEventListener('input',saveDraft);
      el.addEventListener('change',saveDraft);
    });
  }

  function addTrip(){
    collect();
    data.pastTrips=data.pastTrips||[];
    data.pastTrips.push({title:'رحلة جديدة',date:'',description:'',cover:'',images:[],videos:[],visible:true});
    renderTrips();
    saveDraft();
  }

  function publish(){
    collect();
    saveDraft();
    const payload=JSON.stringify(data,null,2);
    const filename='request-'+Date.now()+'.json';
    const url=NEW_FILE_BASE+'?filename='+encodeURIComponent(filename)+'&value='+encodeURIComponent(payload);
    setStatus('تم حفظ المسودة. جارٍ فتح صفحة النشر الجاهزة على GitHub...');
    window.open(url,'_blank');
  }

  const draft=loadDraft();
  fetch(DATA_URL,{cache:'no-store'})
    .then(r=>r.ok?r.json():Promise.reject(new Error('تعذر تحميل البيانات')))
    .then(remote=>{
      data=draft||remote||{};
      fill();
      bindAutosave();
      setStatus(draft?'تم استرجاع المسودة المحفوظة تلقائيًا.':'تم تحميل بيانات الموقع.');
    })
    .catch(e=>{
      if(draft){data=draft;fill();bindAutosave();setStatus('تم استرجاع المسودة المحفوظة تلقائيًا.');}
      else setStatus(e.message);
    });

  $('addTrip').onclick=addTrip;
  $('saveAll').onclick=publish;
  $('saveAllBottom').onclick=publish;
})();