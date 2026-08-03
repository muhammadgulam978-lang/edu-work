(function(){
  'use strict';
  const form=document.getElementById('admissionWizard'); if(!form)return;
  const stepInput=document.getElementById('currentStep');
  let step=Math.max(1,Math.min(7,Number(stepInput.value)||1));
  const steps=[...document.querySelectorAll('.ad-step')];
  const tabs=[...document.querySelectorAll('[data-step-target]')];
  const previous=document.getElementById('previousStep');
  function show(next){step=Math.max(1,Math.min(7,next));stepInput.value=step;steps.forEach(el=>el.classList.toggle('active',Number(el.dataset.step)===step));tabs.forEach(el=>{const n=Number(el.dataset.stepTarget);el.classList.toggle('active',n===step);el.classList.toggle('complete',n<step)});form.classList.toggle('step-final',step===7);previous.disabled=step===1;window.scrollTo({top:0,behavior:'smooth'});}
  tabs.forEach(el=>el.addEventListener('click',()=>show(Number(el.dataset.stepTarget))));
  previous.addEventListener('click',()=>show(step-1));show(step);
  form.addEventListener('submit',event=>{const action=event.submitter&&event.submitter.value;if(action==='save_continue'){const missing=[...steps[step-1].querySelectorAll('[required]')].find(field=>!field.value.trim());if(missing){event.preventDefault();missing.focus();missing.reportValidity();}}});

  const nameInput=form.querySelector('[name=name]');
  if(nameInput)nameInput.addEventListener('input',()=>document.getElementById('summaryName').textContent=nameInput.value||'Not entered');
  const guardianRows=document.getElementById('guardianRows');
  document.getElementById('addGuardian').addEventListener('click',()=>{const fragment=document.getElementById('guardianTemplate').content.cloneNode(true);const primary=fragment.querySelector('[name=guardian_primary]');if(primary)primary.value='0';guardianRows.appendChild(fragment)});
  guardianRows.addEventListener('click',event=>{const button=event.target.closest('.remove-guardian');if(button&&guardianRows.children.length>1)button.closest('.guardian-row').remove()});
  guardianRows.addEventListener('change',event=>{if(event.target.name==='guardian_primary'&&event.target.value==='1'){guardianRows.querySelectorAll('[name=guardian_primary]').forEach(el=>{if(el!==event.target)el.value='0'})}});

  const year=document.getElementById('academicYear'),klass=document.getElementById('admissionClass'),section=document.getElementById('admissionSection');
  let sectionData=[];
  async function loadSections(){if(!year.value||!klass.value){section.innerHTML='<option value="">Select class and year</option>';return}const selected=section.dataset.selected||section.value;const response=await fetch(`${window.admissionLookupUrl}?academic_year_id=${encodeURIComponent(year.value)}&class_id=${encodeURIComponent(klass.value)}`,{headers:{'X-Requested-With':'XMLHttpRequest'}});const data=await response.json();sectionData=data.sections||[];section.innerHTML='<option value="">Select section</option>'+sectionData.map(item=>`<option value="${item.id}" ${String(item.id)===String(selected)?'selected':''}>${item.name} - ${item.remaining} seats</option>`).join('');section.dataset.selected='';updateSectionContext()}
  function updateSectionContext(){const item=sectionData.find(row=>String(row.id)===String(section.value));document.getElementById('capacityText').textContent=item?`${item.enrolled} / ${item.capacity} enrolled (${item.remaining} available)`:'Select a section';document.getElementById('teacherText').textContent=item?(item.teacher?`Class teacher: ${item.teacher}`:'No class teacher assigned'):'Teacher will appear here';const classLabel=klass.options[klass.selectedIndex]?.text||'Class';const sectionLabel=section.options[section.selectedIndex]?.text.split(' - ')[0]||'Section';document.getElementById('summaryPlacement').textContent=section.value?`${classLabel} / ${sectionLabel}`:'Select class and section'}
  year.addEventListener('change',loadSections);klass.addEventListener('change',loadSections);section.addEventListener('change',updateSectionContext);loadSections().catch(()=>{});
  const enabled=document.getElementById('transportEnabled'),route=document.getElementById('transportRoute');function transportState(){route.disabled=!enabled.checked;if(!enabled.checked)route.value=''}enabled.addEventListener('change',transportState);transportState();
})();
