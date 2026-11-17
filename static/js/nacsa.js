(function(){
  var $=function(s,c){return (c||document).querySelector(s)},$$=function(s,c){return Array.prototype.slice.call((c||document).querySelectorAll(s))};
  // sidebar toggle (mobile)
  var mb=$('.menu-btn'),sb=$('.sidebar');
  if(mb&&sb){mb.addEventListener('click',function(){sb.classList.toggle('open')});
    document.addEventListener('click',function(e){if(sb.classList.contains('open')&&!sb.contains(e.target)&&!mb.contains(e.target))sb.classList.remove('open')})}
  // profile dropdown
  var ub=$('.userbox'),dd=$('.dropdown');
  if(ub&&dd){ub.addEventListener('click',function(e){e.stopPropagation();dd.classList.toggle('open')});document.addEventListener('click',function(){dd.classList.remove('open')})}
  // show/hide password
  $$('.pwbox button').forEach(function(b){b.addEventListener('click',function(){var i=b.parentNode.querySelector('input');i.type=i.type==='password'?'text':'password';b.textContent=i.type==='password'?'Show':'Hide'})});
  // confirm modal for [data-confirm] forms/links
  var bg=document.createElement('div');bg.className='modal-bg';
  bg.innerHTML='<div class="modal" role="dialog" aria-modal="true"><h3>Please confirm</h3><p class="muted" id="cm-text"></p><div class="actions" style="justify-content:flex-end;margin-top:16px"><button class="btn btn-outline" id="cm-no" type="button">Cancel</button><button class="btn btn-danger" id="cm-yes" type="button">Confirm</button></div></div>';
  document.body.appendChild(bg);var pending=null;
  function ask(msg,run){$('#cm-text',bg).textContent=msg;bg.classList.add('open');pending=run}
  $('#cm-no',bg).onclick=function(){bg.classList.remove('open');pending=null};
  $('#cm-yes',bg).onclick=function(){bg.classList.remove('open');if(pending)pending();pending=null};
  $$('form[data-confirm]').forEach(function(f){f.addEventListener('submit',function(e){if(f.dataset.ok)return;e.preventDefault();ask(f.dataset.confirm,function(){f.dataset.ok=1;f.submit()})})});
  // loading indicator on submit/navigation + prevent double submit
  var bar=document.createElement('div');bar.className='loading-bar';document.body.appendChild(bar);
  $$('form').forEach(function(f){f.addEventListener('submit',function(){if(f.dataset.confirm&&!f.dataset.ok)return;bar.style.width='80%';
    $$('button[type=submit]',f).forEach(function(b){setTimeout(function(){b.disabled=true;b.dataset.t=b.innerHTML;b.innerHTML='Saving…'},10)})})});
  window.addEventListener('pageshow',function(){bar.style.width='0';$$('button[type=submit]').forEach(function(b){if(b.dataset.t){b.disabled=false;b.innerHTML=b.dataset.t}})});
  // offline notice (poor connectivity)
  var off=$('.offline');function net(){if(off)off.classList.toggle('show',!navigator.onLine)}window.addEventListener('online',net);window.addEventListener('offline',net);net();
  function esc(t){return String(t).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  // multi-step form
  $$('[data-steps]').forEach(function(form){
    var panes=$$('.step-pane',form),btns=$$('.steps-nav button',form),i=0,max=panes.length-1;
    function show(n){i=n;panes.forEach(function(p,k){p.classList.toggle('active',k===n)});btns.forEach(function(b,k){b.classList.toggle('active',k===n);b.classList.toggle('done',k<n)});
      $('.prev',form).style.display=n===0?'none':'';$('.next',form).style.display=n===max?'none':'';$('.finish',form).style.display=n===max?'':'none';window.scrollTo(0,0);if(n===max)review()}
    function valid(n){var ok=true;$$('input,select,textarea',panes[n]).forEach(function(el){if(!el.checkValidity()){ok=false;el.reportValidity()}});return ok}
    function review(){var out=$('#review-box',form);if(!out)return;var h='';$$('.step-pane',form).forEach(function(p,k){if(k===max)return;h+='<h3>'+btns[k].textContent+'</h3><dl class="dl">';
      $$('.fgroup',p).forEach(function(g){var l=g.querySelector('label'),el=g.querySelector('input,select,textarea');if(!l||!el)return;var v=el.tagName==='SELECT'?(el.options[el.selectedIndex]||{}).text:el.value;h+='<dt>'+esc(l.textContent.replace('*',''))+'</dt><dd>'+esc(v||'—')+'</dd>'});h+='</dl>'});out.innerHTML=h}
    $('.next',form).onclick=function(){if(valid(i))show(i+1)};$('.prev',form).onclick=function(){show(i-1)};
    btns.forEach(function(b,k){b.type='button';b.onclick=function(){if(k<=i||valid(i))show(k)}});
    var firstErr=panes.findIndex(function(p){return p.querySelector('.err')});show(firstErr>=0?firstErr:0)});
  // auto-submit filters on select change
  $$('form.filters select[data-auto]').forEach(function(s){s.addEventListener('change',function(){s.form.submit()})});
  // simple table search helper
  $$('[data-print]').forEach(function(b){b.addEventListener('click',function(){window.print()})});
})();
