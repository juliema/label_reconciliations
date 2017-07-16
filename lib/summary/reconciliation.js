const users = document.querySelector('#users button');
const tbody = document.querySelector('#details tbody');
const thead = document.querySelector('#details thead');
const filter = document.querySelector('#details select');
const detailRows = document.querySelectorAll('#details tbody tr');

function toggleUsers(event) {
  const div = document.querySelector('#users .users-container');
  div.classList.toggle('expanded');
  event.target.classList.toggle('expanded');
}

function toggleClosed(event) {
  if (! event.target.matches('button')) { return; }
  const tr = event.target.parentElement.parentElement;
  const subjectId = tr.dataset.subjectId;
  const selector = '#details tbody tr[data-subject-id="' + subjectId + '"]';
  const trs = document.querySelectorAll(selector);
  trs.forEach(function(r) { r.classList.toggle('closed'); });
}

function toggleAllClosed(event) {
  if (! event.target.matches('button')) { return; }
  const tr = event.target.parentElement.parentElement;
  const selector = '#details tbody tr';
  const trs = document.querySelectorAll(selector);
  tr.classList.toggle('closed');
  if (tr.classList.contains('closed')) {
    trs.forEach(function(r) { r.classList.add('closed'); });
  } else {
    trs.forEach(function(r) { r.classList.remove('closed'); });
  }
}

function filterChange() {
  const filterValue = this.value;
  if (filterValue == '__off__') {
    detailRows.forEach(function(row) { row.classList.remove('hide'); });
  } else if (filterValue == '__all__') {
    detailRows.forEach(function(row) {
      if (row.dataset.problems) {
        row.classList.remove('hide');
      } else {
        row.classList.add('hide');
      }
    });
  } else {
    detailRows.forEach(function(row) {
      if (row.dataset.problems.indexOf(filterValue) > -1) {
        row.classList.remove('hide');
      } else {
        row.classList.add('hide');
      }
    });
  }
}

users.addEventListener('click', toggleUsers);
tbody.addEventListener('click', toggleClosed);
thead.addEventListener('click', toggleAllClosed);
filter.addEventListener('change', filterChange);
