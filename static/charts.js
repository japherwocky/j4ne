var margin = {top: 20, right: 80, bottom: 30, left: 50},
    width = 960 - margin.left - margin.right,  // todo, set width & height based on actual screen size
    height = 500 - margin.top - margin.bottom;

var x = d3.time.scale()
    .range([0, width]);

var y = d3.scale.linear()
    .range([height, 0]);

var color = d3.scale.category10();

var xAxis = d3.svg.axis()
    .scale(x)
    .orient("bottom");

var yAxis = d3.svg.axis()
    .scale(y)
    .orient("left");

var line = d3.svg.line()
    .interpolate("basis")
    .x(function(d) { return x(new Date(d.key)); })
    .y(function(d) { return y(d.values); });

var svg = d3.select("body").append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
  .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");



// grab our data and bucket it appropriately
d3.json("/api/messages/", function(error, data) {

    // cast our unix timestamps to local datetimes
    window.data = data.data.map( function(d) { 
        d.datetime = new Date(d.timestamp * 1000); 

        d.datetime.setSeconds( 0 );
        d.datetime.setMinutes( d.datetime.getMinutes() - d.datetime.getMinutes() % 5);

        return d
    });

    window.nested = d3.nest()
        .key( function (d) { return d.channel }) 
        .key( function (d) { return d.datetime })
        .rollup( function (d) { return d.length})
        .entries( window.data);

    var channels = window.nested.map( function(d) {return d.key});

    color.domain(channels);
    x.domain( d3.extent(data.data, function(d) {return new Date(d.datetime)}) );
    y.domain([
        d3.min( nested, function(d) { return d3.min(d.values, function (e) {return e.values})}),
        d3.max( nested, function(d) { return d3.max(d.values, function (e) {return e.values})})
        ])

    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);

    svg.append("g")
            .attr("class", "y axis")
            .call(yAxis)
        .append("text")
            .attr("transform", "rotate(-90)")
            .attr("y", 6)
            .attr("dy", ".71em")
            .style("text-anchor", "end")
            .text("Chat Activity");

    var channel = svg.selectAll(".channel")
        .data(nested)
        .enter().append("g")
        .attr("class", "channel");

    channel.append("path")
        .attr("class", "line")
        .attr("d", function(d) { return line(d.values); })
        .style("stroke", function(d) { return color(d.key); });


    })


