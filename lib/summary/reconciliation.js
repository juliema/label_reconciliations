const None = null;
const args = {{args}};
const filters = {{filters}};
const details = {{details}};

var currentPage = 0;
var currentFilter = 'Show All';

const toggleClosed = function() {
  const groupBy =  d3.select(d3.event.target.parentElement.parentElement).attr('data-group-by');
  const selector = '#details tbody tr[data-group-by="' + groupBy + '"]';
  const tr = document.querySelectorAll(selector);
  tr.forEach(function(r) { r.classList.toggle('closed'); });
}

const toggleAllClosed = function(event) {
  const selector = '#details tbody tr';
  const tr = document.querySelectorAll(selector);
  tr.classList.toggle('closed');
  if (tr.classList.contains('closed')) {
    tr.forEach(function(r) { r.classList.add('closed'); });
  } else {
    tr.forEach(function(r) { r.classList.remove('closed'); });
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

const rowData = function() {
  const rows = [];
  var beg = (currentPage - 1) * args.page_size;
  var end = beg + args.page_size;

  filters[currentFilter].slice(beg, end).forEach(function (id) {

    var row = details['reconciled'][id];
    row[args.group_by] = id;
    row[args.key_column] = '';
    row.__group_by__ = id;
    rows.push(row);

    row = details['explanations'][id];
    row[args.group_by] = '';
    row[args.key_column] = '';
    row.__group_by__ = id;
    rows.push(row);

    details['unreconciled'][id].forEach(function(row) {
      row[args.group_by] = '';
      row.__group_by__ = id;
      rows.push(row);
    });
  });

  return rows;
};

function showPage(rows) {

  const tr = d3.select('#details>table>tbody').selectAll('tr')
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
        var cls = 'closed'
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

  const td = d3.selectAll('#details>table>tbody>tr').selectAll('td')
    .data(function(d) {
      const data = [''];
      details.columns.forEach(function(c) {
        data.push(d[c] || '');
      });
      return data;
    });

  td.enter()
    .append('td')
      .text(function(d) { return d; });
  td.merge(td);
  td.exit().remove();

  const button = d3.selectAll('#details>table>tbody>tr.reconciled').selectAll('td:first-child')
    .append('button')
      .attr('title', 'Open or close this subject')
      .on('click', toggleClosed);
}

const nextPage = function() {
  currentPage++;
  const rows = rowData();
  showPage(rows);
}

document.querySelector('#details thead button').addEventListener('click', toggleAllClosed);
document.querySelector('#next-page').addEventListener('click', nextPage);

nextPage();
