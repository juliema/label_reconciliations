const None = null;  // Python vs Javascript. Only used for the args variable so far
const args = {{args | safe}};
const columns = {{columns | safe}};
const filters = {{filters | safe}};
const groups = {{groups | safe}};
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

    // Build the reconciled row. This is the first row in the group.
    rows.push(buildReconciledRowData(subject['reconciled'], subject['explanations'], id));

    // Build the explanations row. This is the second row in the group.
    rows.push(buildExplanationRowData(subject['explanations'], id));

    // Build the unreconciled rows. These are the third thru n rows in the group.
    subject['unreconciled'].forEach(function(unreconciled) {
      rows.push(buildUnreconciledRowData(unreconciled, id));
    });
  });

  return rows;
};

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
  const isClosed = event.target.parentElement.parentElement.classList.contains('closed');
  const groupBy = event.target.dataset.groupBy;
  const selector = '#groups tbody tr[data-group-by="' + groupBy + '"]';
  const trs = document.querySelectorAll(selector);
  trs.forEach(function(r) { r.classList.toggle('closed'); });
  groupState[groupBy] = isClosed ? '' : 'closed';
}
tbody.addEventListener('click', toggleClosed);

// Like the toggleClosed function (above) but it's for all groups of records.
const toggleAllClosed = function(event) {
  var cls = !d3.select('#groups thead tr').attr('class');
  d3.select('#groups thead tr').classed('closed', cls);
  d3.selectAll('#groups tbody tr').classed('closed', cls);
  cls = cls ? 'closed' : '';
  filters['Show All'].forEach(function(id) { groupState[id] = cls; });
}

var maxPage = 0;

const changePage = function() {
  var page = +d3.select('#groups .pager').property('value');
  var filter = d3.select('#groups .filter').property('value');
  page = page < 1 ? 1 : page;
  page = page > maxPage ? maxPage : page;
  d3.select('#groups .pager').property('value', page);
  const data = rowData(page, filter);
  buildPage(data);
}

const filterChange = function() {
  const filter = d3.select('#groups .filter').property('value');
  maxPage = Math.ceil(filters[filter].length / args.page_size);
  d3.select('#groups .pager').property('max', maxPage);
  d3.select('#groups .max-page').text('of ' + maxPage);
  changePage();
}

d3.select('#groups .pager').on('change', changePage);
d3.select('#groups .filter').on('change', filterChange);
d3.select('#groups thead button').on('click', toggleAllClosed);

filterChange();
