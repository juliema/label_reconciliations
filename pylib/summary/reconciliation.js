// Python vs Javascript. Only needed by the args variable so far
const None = null;
const True = true;
const False = false;

const args = {{args | safe}};
const columns = {{columns | safe}};
const filters = {{filters | safe}};
const is_problem = RegExp("{{problem_pattern}}", 'i');
const tbody = document.querySelector('#groups tbody');

// Save the group's open/close state so it will remain consistent between
// Page and filter changes.
const groupState = {};
filters['Show All'].forEach(function(id) {
  groupState[id] = 'closed';
});

// Move the detail data into a form that we can use for displaying on the page.
// We will feed it an array of objects, one for each table row. Within each row
// we will have have an array of cells (td) and an object of row metadata. Each
// cell (td) is an object with the content, class, title, etc.
const rowData = function(page, filter) {
  const rows = [];
  const beg = (page - 1) * args.page_size;
  const end = beg + args.page_size;

  filters[filter].slice(beg, end).forEach(function(id, i) {
    const subject = groups[id];

    rows.push(buildReconciledRowData(subject['reconciled'], subject['explanations'], id));

    rows.push(buildExplanationRowData(subject['explanations'], id));

    subject['unreconciled'].forEach(function(unreconciled) {
      rows.push(buildUnreconciledRowData(unreconciled, id));
    });
  });

  return rows;
};

// Build the reconciled row. This is the first row in the group.
const buildReconciledRowData = function(reconciled, explanations, groupBy) {
  const tr = {
    rowMetadata: { groupBy: groupBy, cls: 'reconciled' },
    td: [  // Setup always filled row cells
      { content: '<button data-group-by="' + groupBy + '" title="Open or close this subject"></button>' },
      { content: groupBy }
    ]
  };
  columns.forEach(function(col, i) {
    if (col != args.group_by) {
      tr.td.push({
        content: reconciled[col] || '',
        title: explanations[col],
        cls: is_problem.test(explanations[col]) ? 'problem' : null
      });
    }
  });
  return tr;
};

// Build the explanations row. This is the second row in the group.
const buildExplanationRowData = function(explanations, groupBy) {
  const tr = {
    rowMetadata: { groupBy: groupBy, cls: 'explanations' },
    td: [  // Setup always empty row cells
      { content: '' },  // open/close row group button
      { content: '' }   // group by cell (typically: subject_id)
    ]
  };
  columns.forEach(function(col, i) {
    if (col != args.group_by) {
      tr.td.push({
        content: explanations[col] || '',
        cls: explanations[col] ? 'filled' : null
      });
    }
  });
  return tr;
};

// Build the unreconciled rows. These are the third thru n rows in the group.
const buildUnreconciledRowData = function(unreconciled, groupBy) {
  tr = {
    rowMetadata: { groupBy: groupBy, cls: 'unreconciled' },
    td: [  // Setup always empty row cells
      { content: '' },  // open/close row group button
      { content: '' }   // group by cell (typically: subject_id)
    ]
  };
  columns.forEach(function(col, i) {
    if (col != args.group_by) {
      tr.td.push({ content: unreconciled[col] || '' });
    }
  });
  return tr;
};

// Given a list of rows (formatted by rowData) build a page of transcriptions reconciliation
const buildPage = function(rows) {

  // Remove old rows
  while (tbody.firstChild) {
    tbody.removeChild(tbody.firstChild);
  }

  // Add new rows
  rows.forEach(function(row, i) {

    // Build the table's rows
    const tr = document.createElement('tr');
    const id = row.rowMetadata.groupBy;
    tr.classList.add(row.rowMetadata.cls);
    if (groupState[id]) { tr.classList.add(groupState[id]); }
    tr.setAttribute('data-group-by', id);

    // Build the row's cells
    row.td.forEach(function(cell) {
      const td = document.createElement('td');
      if (cell.cls) { td.classList.add(cell.cls); }
      if (cell.title) { td.setAttribute('title', cell.title); }
      td.innerHTML = cell.content;
      tr.appendChild(td);
    });

    tbody.appendChild(tr);
  });
}

// Toggle a group of rows open/closed. That is we will show/hide all records
// for a group. Closing them leaves only the first record (the reconciled one)
// visible.
const toggleClosed = function(event) {
  if (! event.target.matches('button')) { return; }
  const groupBy = event.target.dataset.groupBy;
  const selector = '#groups tbody tr[data-group-by="' + groupBy + '"]';
  const trs = document.querySelectorAll(selector);
  trs.forEach(function(r) { r.classList.toggle('closed'); });
  const isClosed = event.target.parentElement.parentElement.classList.contains('closed');
  groupState[groupBy] = isClosed ? 'closed' : '';
}

// Like the toggleClosed function (above) but it's for all groups of records.
const toggleAllClosed = function(event) {
  const header = document.querySelector('#groups thead tr');
  const cls = header.classList.contains('closed') ? '' : 'closed';
  const trs = document.querySelectorAll('#groups tbody tr');
  header.classList.toggle('closed');
  if (cls) {
    trs.forEach(function(r) { r.classList.add('closed'); });
  } else {
    trs.forEach(function(r) { r.classList.remove('closed'); });
  }
  filters['Show All'].forEach(function(id) { groupState[id] = cls; });
}

var maxPage = 0;

const changePage = function() {
  const pager = document.querySelector('#groups .pager');
  const filter = document.querySelector('#groups .filter').value;
  var page = +pager.value;
  page = page < 1 ? 1 : page;
  page = page > maxPage ? maxPage : page;
  pager.value = page;
  const data = rowData(page, filter);
  buildPage(data);
}

const filterChange = function() {
  const filter = document.querySelector('#groups .filter').value;
  maxPage = Math.ceil(filters[filter].length / args.page_size);
  document.querySelector('#groups .pager').setAttribute('max', maxPage);
  document.querySelector('#groups .max-page').innerHTML = 'of ' + maxPage;
  changePage();
}

tbody.addEventListener('click', toggleClosed);
document.querySelector('#groups .pager').addEventListener('change', changePage);
document.querySelector('#groups .filter').addEventListener('change', filterChange);
document.querySelector('#groups thead button').addEventListener('click', toggleAllClosed);

document.querySelector('#groups .first-page').addEventListener('click', function() {
  const pager = document.querySelector('#groups .pager');
  pager.value = 1;
  changePage();
});

document.querySelector('#groups .previous-page').addEventListener('click', function() {
  const pager = document.querySelector('#groups .pager');
  pager.value = +pager.value - 1;
  changePage();
});

document.querySelector('#groups .next-page').addEventListener('click', function() {
  const pager = document.querySelector('#groups .pager');
  pager.value = +pager.value + 1;
  changePage();
});

document.querySelector('#groups .last-page').addEventListener('click', function() {
  const pager = document.querySelector('#groups .pager');
  pager.value = maxPage;
  changePage();
});

filterChange();
