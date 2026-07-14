const classSelect = document.getElementById('id_class');
const sectionSelect = document.getElementById('id_section');
const subjectSelect = document.getElementById('id_subject');
const daySelect = document.getElementById('id_day');
const periodSelect = document.getElementById('id_period');
const teacherSelect = document.getElementById('id_teacher');
const assignedTable = document.getElementById('assigned-classes-table');
const toast = document.getElementById('toast');

function showToast(message) {
  toast.textContent = message;
  toast.style.display = 'block';
  setTimeout(() => toast.style.display = 'none', 4000);
}

// ------------------- Class Change -------------------
classSelect.addEventListener('change', function () {
  const classId = this.value;

  sectionSelect.innerHTML = '<option value="">Loading...</option>';
  subjectSelect.innerHTML = '<option value="">Select Section First</option>';
  daySelect.innerHTML = '<option value="">Select Subject First</option>';
  periodSelect.innerHTML = '<option value="">Select Day First</option>';
  teacherSelect.innerHTML = '<option value="">Select Subject First</option>';

  if (!classId) return;

  fetch(`/admin_panel/ajax/get_sections_for_class/?class_id=${classId}`)
    .then(res => res.json())
    .then(sections => {
      sectionSelect.innerHTML = '<option value="">Select Section</option>';
      sections.forEach(sec => {
        sectionSelect.innerHTML += `<option value="${sec.id}">${sec.name}</option>`;
      });
    });
});

// ------------------- Section Change -------------------
sectionSelect.addEventListener('change', function () {
  const sectionId = this.value;

  subjectSelect.innerHTML = '<option value="">Loading...</option>';
  daySelect.innerHTML = '<option value="">Select Subject First</option>';
  periodSelect.innerHTML = '<option value="">Select Day First</option>';
  teacherSelect.innerHTML = '<option value="">Select Subject First</option>';

  if (!sectionId) return;

  fetch(`/admin_panel/ajax/get_subjects_for_section/?section_id=${sectionId}`)
    .then(res => res.json())
    .then(subjects => {
      console.log("Subjects response:", subjects); // Debugging
      subjectSelect.innerHTML = '<option value="">Select Subject</option>';
      subjects.forEach(sub => {
        let option = document.createElement('option');
        option.value = sub.id;
        // ✅ safe fallback: jo bhi field backend bheje
        option.text = sub.name || sub.subject_name || sub.title || "Unnamed Subject";
        subjectSelect.add(option);
      });
    });
});

// ------------------- Subject Change -------------------
subjectSelect.addEventListener('change', function () {
  const subjectId = this.value;
  const sectionId = sectionSelect.value;

  daySelect.innerHTML = '<option value="">Loading...</option>';
  periodSelect.innerHTML = '<option value="">Select Day First</option>';
  teacherSelect.innerHTML = '<option value="">Loading...</option>';

  if (!subjectId || !sectionId) return;

  fetch(`/admin_panel/ajax/get_days_for_subject/?subject_id=${subjectId}&section_id=${sectionId}`)
    .then(res => res.json())
    .then(days => {
      daySelect.innerHTML = '<option value="">Select Day</option>';
      days.forEach(day => {
        daySelect.innerHTML += `<option value="${day.day}">${day.label}</option>`;
      });
    });

  fetch(`/admin_panel/ajax/subject_periods/?subject_id=${subjectId}`)
    .then(res => res.json())
    .then(data => {
      teacherSelect.innerHTML = '<option value="">Select Teacher</option>';
      data.teachers.forEach(t => {
        teacherSelect.innerHTML += `<option value="${t.id}">${t.name}</option>`;
      });
    });
});

// ------------------- Day Change -------------------
daySelect.addEventListener('change', function () {
  const subjectId = subjectSelect.value;
  const selectedDay = this.value;
  const sectionId = sectionSelect.value;

  if (!subjectId || !selectedDay || !sectionId) return;

  fetch(`/admin_panel/ajax/time_slots/?subject_id=${subjectId}&day=${selectedDay}&section_id=${sectionId}`)
    .then(res => res.json())
    .then(data => {
      periodSelect.innerHTML = '';
      data.periods.forEach(p => {
        periodSelect.innerHTML += `<option value="${p.id}">${p.label}</option>`;
      });

      const assignable = data.assignable || 0;
      let lastValid = [];

      periodSelect.addEventListener('change', function () {
        const selected = Array.from(this.selectedOptions);
        if (selected.length > assignable) {
          alert(`You can only assign ${assignable} period(s) for this subject.`);
          Array.from(this.options).forEach(opt => opt.selected = lastValid.includes(opt.value));
        } else {
          lastValid = selected.map(opt => opt.value);
        }
      });
    });
});

// ------------------- Load Assigned Classes -------------------
function loadAssignedClasses() {
  fetch('/admin_panel/ajax/get_assigned_classes/')
    .then(res => res.json())
    .then(assignments => {
      assignedTable.innerHTML = '';
      if (assignments.length === 0) {
        const colCount = document.querySelectorAll('thead th').length;
        assignedTable.innerHTML = `<tr><td colspan="${colCount}" class="text-center text-gray-500 py-4">No assigned classes found.</td></tr>`;
        return;
      }
      assignments.forEach(a => {
        assignedTable.innerHTML += `
          <tr class="text-sm sm:text-base text-gray-600">
            <td class="px-4 sm:px-6 py-4 whitespace-nowrap">${a.class_name}</td>
            <td class="px-4 sm:px-6 py-4 whitespace-nowrap">${a.section_name}</td>
            <td class="px-4 sm:px-6 py-4 whitespace-nowrap"><span class="assignment-badge assignment-badge-subject">${a.subject_name}</span></td>
            <td class="px-4 sm:px-6 py-4 whitespace-nowrap"><span class="assignment-badge assignment-badge-day">${a.day_label}</span></td>
            <td class="px-4 sm:px-6 py-4 whitespace-nowrap">${a.period_label}</td>
            <td class="px-4 sm:px-6 py-4 whitespace-nowrap"><span class="assignment-badge assignment-badge-teacher">${a.teacher_name}</span></td>
            <td class="px-4 sm:px-6 py-4 whitespace-nowrap">
              <button data-id="${a.id}" class="text-red-600 hover:text-red-800">Delete</button>
            </td>
          </tr>`;
      });
    });
}

document.addEventListener('DOMContentLoaded', loadAssignedClasses);

// ------------------- Form Submit -------------------
document.querySelector('form').addEventListener('submit', function (e) {
  e.preventDefault();
  const form = this;
  const formData = new FormData(form);
  fetch(form.action, {
    method: 'POST',
    body: formData,
    headers: { 'X-CSRFToken': formData.get('csrfmiddlewaretoken') }
  })
  .then(async res => res.ok ? res.json() : Promise.reject(await res.json()))
  .then(data => {
    if (data.success) {
      loadAssignedClasses();
      form.reset();
      sectionSelect.innerHTML = '<option value="">Select Class First</option>';
      subjectSelect.innerHTML = '<option value="">Select Section First</option>';
      daySelect.innerHTML = '<option value="">Select Subject First</option>';
      periodSelect.innerHTML = '<option value="">Select Day First</option>';
      teacherSelect.innerHTML = '<option value="">Select Subject First</option>';
      classSelect.dispatchEvent(new Event('change'));
      showToast("Class assigned successfully!");
    }
  })
  .catch(err => {
    let msg = "An error occurred.";
    if (err.error?.__all__) msg = err.error.__all__[0].message;
    else for (let field in err.error) { msg = err.error[field][0].message; break; }
    showToast(msg);
  });
});

// ------------------- Delete Assigned Class -------------------
assignedTable.addEventListener('click', function (e) {
  if (e.target.tagName === 'BUTTON' && e.target.textContent === 'Delete') {
    const assignmentId = e.target.dataset.id;
    fetch(`/admin_panel/ajax/delete_assignment/${assignmentId}/`, {
      method: 'DELETE',
      headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value }
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        loadAssignedClasses();
        showToast("Assignment deleted successfully!");
      } else showToast(data.error || "Failed to delete assignment.");
    })
    .catch(() => showToast("An error occurred while deleting."));
  }
});
