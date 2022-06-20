
const data = {{ transcribers | safe }};

if (data && data.length) {
  const formatCount = d3.format(',.0f');

  const svg = d3.select('#users-chart svg');

  const pad = { top: 20, bottom: 100, left: 100, right: 100 };
  const shiftLeftHi = 0;
  const widthLo = 40;
  const widthHi = +svg.attr('width') - pad.left - pad.right - widthLo;
  const height = +svg.attr('height') - pad.top - pad.bottom;
  const g = svg.append('g').attr('transform', 'translate(' + pad.left + ',' + pad.top + ')');

  function value(d) {
    return d.count;
  }

  const xLo = d3.scaleLinear()
    .domain([1, 3])
    .rangeRound([0, widthLo]);

  const xHi = d3.scaleLinear()
    .domain([3, d3.max(data, value) * 1.1])
    .rangeRound([3, widthHi]);

  const binsLo = d3.histogram()
    .value(value)
    .domain(xLo.domain())
    .thresholds(xLo.ticks(2))
    (data);
  binsLo.splice(binsLo.length - 1);

  const binsHi = d3.histogram()
    .value(value)
    .domain(xHi.domain())
    .thresholds(xHi.ticks(20))
    (data);

  const y = d3.scaleLinear()
    .domain([0, d3.max(binsLo.concat(binsHi), function(d) { return d.length; })])
    .range([height, 0]);

  const barLo = g.selectAll('.bar-lo')
    .data(binsLo)
    .enter()
      .append('g')
        .attr('class', 'bar bar-lo')
        .attr('transform', function(d) {
          return 'translate(' + xLo(d.x0) + ',' + y(d.length) + ')';
        });

  const barHi = g.selectAll('.bar-hi')
    .data(binsHi)
    .enter()
      .append('g')
        .attr('class', 'bar bar-hi')
        .attr('transform', function(d) {
          return 'translate(' + (xHi(d.x0) + widthLo - shiftLeftHi) + ',' + y(d.length) + ')';
        });

  function barHeight(d) {
    const h = height - y(d.length);
    d.height = h;
    return h;
  }

  barLo.append('rect')
    .attr('x', 1)
    .attr('width', function(d) { return xLo(d.x1) - xLo(d.x0) - 1; })
    .attr('height', barHeight);

  barHi.append('rect')
   .attr('x', 1)
   .attr('width', function(d) { return xHi(d.x1) - xHi(d.x0) - 1; })
   .attr('height', barHeight);

  function barText(d) {
    return d.height >= 15 ? formatCount(d.length) : '';
  }

  barLo.append('text')
    .attr('dy', '0.75em')
    .attr('y', 6)
    .attr('x', function(d) { return (xLo(d.x1) - xLo(d.x0)) / 2 })
    .attr('text-anchor', 'middle')
    .text(barText);

  barHi.append('text')
    .attr('dy', '0.75em')
    .attr('y', 6)
    .attr('x', function(d) { return (xHi(d.x1) - xHi(d.x0)) / 2 })
    .attr('text-anchor', 'middle')
    .text(barText);

  function plural(str, n) {
    str = formatCount(n) + ' ' + str;
    return n == 1 ? str : str + 's';
  }

  function titleText(d) {
    const span = d.x1 - d.x0 - 1;
    if (span) {
      return plural('transcriber', d.length) + ' completed between ' + d.x0 + ' and ' + (d.x0 + span) + ' transcriptions';
    } else {
      return plural('transcriber', d.length) + ' completed ' + plural('transcription', d.x0);
    }
  }

  barLo.append('svg:title')
    .text(titleText);

  barHi.append('svg:title')
    .text(titleText);

  const axisLo = d3.axisBottom()
    .scale(xLo)
    .ticks(2);

  g.append('g')
    .attr('class', 'axis axis--x')
    .attr('transform', 'translate(0,' + height + ')')
    .call(axisLo);

  g.append('g')
    .attr('class', 'axis axis--x')
    .attr('transform', 'translate(' + (widthLo - shiftLeftHi) + ',' + height + ')')
    .call(d3.axisBottom(xHi));

  svg.append('text')
    .attr('text-anchor', 'middle')
    .attr('font-size', '1.25em')
    .attr('transform', 'translate(' + (pad.left * 0.75) + ',' + ((height + pad.top + pad.bottom) / 2) + ')rotate(-90)')
    .text('Number of Transcribers');

  svg.append('text')
    .attr('text-anchor', 'middle')
    .attr('font-size', '1.25em')
    .attr('transform', 'translate(' + ((widthHi + pad.left + pad.right) / 2) + ',' + (height + pad.top + (pad.bottom / 2)) + ')')
    .text('Number of Transcriptions');
}
