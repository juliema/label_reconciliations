const None = null;  // Python vs Javascript. Only used for the args variable so far
const args = {{args | safe}};
const columns = {{columns | safe}};
const filters = {{filters | safe}};
const details = {{details | safe}};

// Toggle a group of rows open/closed. That is we will show/hide all records for a group.
// Closing them leaves the first record (the reconciled one) visible.
const toggleClosed = function() {
  const groupBy =  d3.select(d3.event.target.parentElement.parentElement).attr('data-group-by');
  const selector = '#details tbody tr[data-group-by="' + groupBy + '"]';
  const cls = !d3.select(selector).classed('closed');
  d3.selectAll(selector).classed('closed', cls);
}

// Like the toggleClosed function (above) only for all groups of records.
const toggleAllClosed = function(event) {
  const cls = !d3.select('#details thead tr').classed('closed');
  d3.select('#details thead tr').classed('closed', cls);
  d3.selectAll('#details tbody tr').classed('closed', cls);
}

// Move the detail data into a form that we can use for displaying on the page
const rowData = function(page, filter) {
  const rows = [];
  const beg = (page - 1) * args.page_size;
  const end = beg + args.page_size;

  filters[filter].slice(beg, end).forEach(function(id) {
    const subject = details[id];

    var row = subject['reconciled'];
    row[args.group_by] = id;
    row[args.key_column] = '';
    row.__group_by__ = id;
    rows.push(row);

    row = subject['explanations'];
    row[args.group_by] = '';
    row[args.key_column] = '';
    row.__group_by__ = id;
    rows.push(row);

    subject['unreconciled'].forEach(function(row) {
      row[args.group_by] = '';
      row.__group_by__ = id;
      rows.push(row);
    });
  });

  return rows;
};

function showPage(rows) {

  const tr = d3.select('#details tbody').selectAll('tr')
    .data(rows, function(d) {
      var key;
      if (d[args.group_by]) {
        key = 'r' + d.__group_by__;
      } else if (d[args.key_column]) {
        key = 'u' + d.__group_by__ + ' ' + d[args.key_column];
      } else {
        key = 'e' + d.__group_by__;
      }
      return key;
    });

  tr.enter()
    .append('tr')
      .attr('class', function(d) {
        var cls = d3.select('#details thead tr').classed('closed') ? 'closed' : null;
        if (d[args.group_by]) {
          cls += ' reconciled';
        } else if (d[args.key_column]) {
          cls += ' unreconciled';
        } else {
          cls += ' explanations';
        }
        return cls;
      })
      .attr('data-group-by', function(d) { return d.__group_by__});
  tr.merge(tr);
  tr.exit().remove();

  const td = d3.selectAll('#details tbody tr').selectAll('td')
    .data(function(d) {
      const data = [''];
      columns.forEach(function(c) {
        data.push(d[c] || '');
      });
      return data;
    });

  td.enter()
    .append('td')
      .attr('class', function(d) { return d ? 'filled' : null; })
      .html(function(d) { return d; });
  td.merge(td);
  td.exit().remove();

  const reconciled = d3.selectAll('#details tbody tr.reconciled');

  reconciled.selectAll('td:first-child')
    .append('button')
      .attr('title', 'Open or close this subject')
      .on('click', toggleClosed);
}

var maxPage = 0;
var previousPage = 0;

const changePage = function() {
  var page = +d3.select('#details .pager').property('value');
  var filter = d3.select('#details .filter').property('value');
  page = page < 1 ? 1 : page;
  page = page > maxPage ? maxPage : page;
  d3.select('#details .pager').property('value', page);
  if (page == previousPage) { return; }
  previousPage = page;
  const data = rowData(page, filter);
  showPage(data);
}

function filterChange() {
  const filter = d3.select('#details .filter').property('value');
  maxPage = Math.ceil(filters[filter].length / args.page_size);
  d3.select('#details .pager').property('max', maxPage);
  d3.select('#details .max-page').text('of ' + maxPage);
}

d3.select('#details .pager').on('change', changePage);
d3.select('#details .filter').on('change', filterChange);
d3.select('#details thead button').on('click', toggleAllClosed);

filterChange();
changePage();
