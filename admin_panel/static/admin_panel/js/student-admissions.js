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
  // Missing operational details are intentionally allowed and can be completed later.

  const nameInput=form.querySelector('[name=name]');
  if(nameInput)nameInput.addEventListener('input',()=>document.getElementById('summaryName').textContent=nameInput.value||'Not entered');
  const photoInput=document.getElementById('studentPhotoInput'),photoPreview=document.getElementById('studentPhotoPreview');
  if(photoInput&&photoPreview)photoInput.addEventListener('change',()=>{const file=photoInput.files&&photoInput.files[0];if(!file)return;const reader=new FileReader();reader.onload=()=>{let image=photoPreview.querySelector('img');if(!image){image=document.createElement('img');image.alt='Student photograph preview';photoPreview.prepend(image)}image.src=reader.result};reader.readAsDataURL(file)});
  const guardianRows=document.getElementById('guardianRows');
  document.getElementById('addGuardian').addEventListener('click',()=>{const fragment=document.getElementById('guardianTemplate').content.cloneNode(true);const primary=fragment.querySelector('[name=guardian_primary]');if(primary)primary.value='0';guardianRows.appendChild(fragment)});
  guardianRows.addEventListener('click',event=>{const button=event.target.closest('.remove-guardian');if(button&&guardianRows.children.length>1)button.closest('.guardian-row').remove()});
  guardianRows.addEventListener('change',event=>{if(event.target.name==='guardian_primary'&&event.target.value==='1'){guardianRows.querySelectorAll('[name=guardian_primary]').forEach(el=>{if(el!==event.target)el.value='0'})}});

  const year=document.getElementById('academicYear'),klass=document.getElementById('admissionClass'),section=document.getElementById('admissionSection'),feePlan=document.getElementById('admissionFeePlan');
  let sectionData=[];
  function renderFeePlans(plans, preferred){
    feePlan.replaceChildren(new Option(plans.length?'Select fee plan':'No fee plan available',''));
    plans.forEach(item=>feePlan.add(new Option(item.label,item.id)));
    if(preferred&&plans.some(item=>String(item.id)===String(preferred)))feePlan.value=preferred;
    feePlan.dataset.selected='';
    document.getElementById('feePlanMissing').hidden=!year.value||!klass.value||plans.length>0;
  }
  async function loadSections(preferredPlan){
    if(!year.value||!klass.value){section.innerHTML='<option value="">Select class and year</option>';renderFeePlans([],null);document.getElementById('feePlanMissing').hidden=true;return}
    const selected=section.dataset.selected||section.value;
    const planSelected=preferredPlan||feePlan.dataset.selected||feePlan.value;
    const response=await fetch(`${window.admissionLookupUrl}?academic_year_id=${encodeURIComponent(year.value)}&class_id=${encodeURIComponent(klass.value)}`,{headers:{'X-Requested-With':'XMLHttpRequest'}});
    if(!response.ok)throw new Error('Unable to refresh admission choices.');
    const data=await response.json();sectionData=data.sections||[];
    section.innerHTML='<option value="">Select section</option>'+sectionData.map(item=>`<option value="${item.id}" ${String(item.id)===String(selected)?'selected':''}>${item.name} - ${item.remaining} seats</option>`).join('');
    section.dataset.selected='';renderFeePlans(data.fee_plans||[],planSelected);updateSectionContext();
  }
  function updateSectionContext(){const item=sectionData.find(row=>String(row.id)===String(section.value));document.getElementById('capacityText').textContent=item?`${item.enrolled} / ${item.capacity} enrolled (${item.remaining} available)`:'Select a section';document.getElementById('teacherText').textContent=item?(item.teacher?`Class teacher: ${item.teacher}`:'No class teacher assigned'):'Teacher will appear here';const classLabel=klass.options[klass.selectedIndex]?.text||'Class';const sectionLabel=section.options[section.selectedIndex]?.text.split(' - ')[0]||'Section';document.getElementById('summaryPlacement').textContent=section.value?`${classLabel} / ${sectionLabel}`:'Select class and section'}
  year.addEventListener('change',()=>loadSections().catch(()=>{}));klass.addEventListener('change',()=>loadSections().catch(()=>{}));section.addEventListener('change',updateSectionContext);loadSections().catch(()=>{});
  const feeModal=document.getElementById('feePlanModal');
  const openFeeModal=document.getElementById('openFeePlanModal');
  const feeForm=document.getElementById('feePlanQuickForm');
  const feeError=document.getElementById('feePlanError');
  function closeFeePlanModal(){feeModal.close()}
  if(openFeeModal)openFeeModal.addEventListener('click',()=>{
    if(!year.value||!klass.value)return;
    document.getElementById('feePlanClassLabel').textContent=klass.options[klass.selectedIndex].text;
    document.getElementById('feePlanYearLabel').textContent=year.options[year.selectedIndex].text.replace(' (Active)','');
    feeError.hidden=true;feeModal.showModal();document.getElementById('feePlanName').focus();
  });
  document.getElementById('closeFeePlanModal').addEventListener('click',closeFeePlanModal);
  document.getElementById('cancelFeePlanModal').addEventListener('click',closeFeePlanModal);
  document.getElementById('refreshFeePlans').addEventListener('click',()=>loadSections().catch(()=>{}));
  feeModal.addEventListener('click',event=>{if(event.target===feeModal)closeFeePlanModal()});
  feeForm.addEventListener('submit',async event=>{
    event.preventDefault();feeError.hidden=true;
    const submit=document.getElementById('saveFeePlan');submit.disabled=true;
    const data=new FormData();
    data.append('csrfmiddlewaretoken',feeForm.querySelector('[name=csrfmiddlewaretoken]').value);
    data.append('class_id',klass.value);data.append('academic_year_id',year.value);
    data.append('name',document.getElementById('feePlanName').value.trim());
    feeForm.querySelectorAll('[data-fee-head]').forEach(input=>{if(input.value)data.append(`head_${input.dataset.feeHead}`,input.value)});
    try{
      const response=await fetch(window.admissionFeePlanCreateUrl,{method:'POST',body:data,headers:{'X-Requested-With':'XMLHttpRequest'}});
      const result=await response.json();
      if(!response.ok||!result.success)throw new Error(result.error||'Fee plan could not be created.');
      await loadSections(result.plan.id);closeFeePlanModal();feeForm.reset();
    }catch(error){feeError.textContent=error.message;feeError.hidden=false}
    finally{submit.disabled=false}
  });
  const enabled=document.getElementById('transportEnabled'),route=document.getElementById('transportRoute');function transportState(){route.disabled=!enabled.checked;if(!enabled.checked)route.value=''}enabled.addEventListener('change',transportState);transportState();
})();
