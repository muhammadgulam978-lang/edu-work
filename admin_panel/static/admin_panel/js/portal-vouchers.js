(function(){
  'use strict';
  const root=document.querySelector('[data-voucher-popup]');
  if(!root)return;
  const summaryUrl=root.dataset.summaryUrl;
  const alertBox=document.querySelector('[data-voucher-alert]');
  let current=null;
  let timer=null;
  const csrf=()=>{const match=document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);return match?decodeURIComponent(match[1]):'';};
  const formatDate=value=>new Intl.DateTimeFormat(undefined,{day:'2-digit',month:'short',year:'numeric'}).format(new Date(value+'T00:00:00'));
  function show(data){
    current=data;
    root.querySelector('[data-voucher-title]').textContent=data.title;
    root.querySelector('[data-voucher-student]').textContent=data.student_name+' · '+data.student_id;
    root.querySelector('[data-voucher-issue]').textContent=formatDate(data.issue_date);
    root.querySelector('[data-voucher-due]').textContent=formatDate(data.due_date);
    root.querySelector('[data-voucher-amount]').textContent=data.amount;
    root.querySelector('[data-voucher-view]').href=data.view_url;
    root.querySelector('[data-voucher-download]').href=data.download_url;
    root.hidden=false;
    document.body.style.overflow='hidden';
  }
  function update(payload){
    if(alertBox){
      const count=payload.unread_notifications||0;
      alertBox.hidden=count===0;
      alertBox.querySelector('[data-voucher-alert-count]').textContent=count;
    }
    if(payload.popup&&(!current||current.id!==payload.popup.id))show(payload.popup);
  }
  async function refresh(){
    try{const response=await fetch(summaryUrl,{headers:{'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin'});if(response.ok)update(await response.json());}catch(error){}
  }
  async function close(){
    root.hidden=true;document.body.style.overflow='';
    if(!current)return;
    const dismissUrl=current.dismiss_url;current=null;
    try{await fetch(dismissUrl,{method:'POST',headers:{'X-CSRFToken':csrf(),'X-Requested-With':'XMLHttpRequest'},credentials:'same-origin'});}finally{refresh();}
  }
  root.querySelectorAll('[data-voucher-close]').forEach(button=>button.addEventListener('click',close));
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!root.hidden)close();});
  function connect(){
    const protocol=location.protocol==='https:'?'wss:':'ws:';
    const socket=new WebSocket(protocol+'//'+location.host+'/ws/vouchers/');
    socket.onmessage=refresh;
    socket.onclose=()=>setTimeout(connect,5000);
  }
  refresh();connect();timer=setInterval(refresh,15000);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
})();
