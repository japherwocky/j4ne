var margin = {top: 20, right: 80, bottom: 30, left: 50},
    width = 960 - margin.left - margin.right,  // todo, set width & height based on actual screen size
    height = 250 - margin.top - margin.bottom;

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

// add our SVG element
var svg = d3.select("body").append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
  .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");


// grab our data and bucket it appropriately
d3.json("/api/messages/?network=twitch&channel=sledgethewrestler", function(error, data) {

    // cast our unix timestamps to local datetimes
    window.chatdata = data.data.map( function(d) { 
        d.datetime = new Date(d.timestamp * 1000); 

        d.datetime.setSeconds( 0 );
        d.datetime.setMinutes( d.datetime.getMinutes() - d.datetime.getMinutes() % 5);

        return d
    });

    window.nested = d3.nest()
        .key( function (d) { return d.channel }) 
        .key( function (d) { return d.datetime })
        .rollup( function (d) { return d.length})
        .entries( window.chatdata);

    var channels = window.nested.map( function(d) {return d.key});

    color.domain(channels);

    // set X domain and calculate bar widths
    x.domain( d3.extent(data.data, function(d) {return new Date(d.datetime)}) );
    var xdomain = x.domain();
    var xticks = (xdomain[1] - xdomain[0]) / 60 / 6 / 1000;  // number of 10 minute ticks on the chart
    var barwidth = x.range()[1] / xticks - 5 ;  // magic.. this is slightly too wide for some reason
    // barwidth = barwidth < 1 ? 1 : barwidth;


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
            .text("Chat / 10m");

    // a group per channel we're rendering
    var channel = svg.selectAll(".channel")
        .data(nested)
        .enter().append("g")
        .attr("class", "channel");

    // data as bars, if we're zoomed in enough to see them
    if (barwidth > 1) {
        var bars = channel.each( function(d) {
            // each d comes in as key: date, values: int
            d3.select(this).selectAll('.messagebar')
                .data(d.values)
                .enter()
                .append("rect")
                .attr('class', 'messagebar')
                .attr('x', function(d) {return x(new Date(d.key))})
                .attr('y', function(d) {return y(d.values)})
                .attr('width', barwidth)
                .attr('height', function(d) {return height - y(d.values)})
            })
    }

    // data as a line
    channel.append("path")
        .attr("class", "line")
        .attr("d", function(d) { return line(d.values); })
        .style("stroke", function(d) { return color(d.key); });


    })


function loadData(channel) {

    // recursively load all back data
    var now = moment.utc().toISOString(),
        apipath = 'api/events/?network=twitch&channel=';

    apipath += channel;

    pager(now);

    function pager(oldest) {
        var thispath = apipath + '&before='+oldest;
        d3.json(thispath, function(error, data) {

            if (error) { console.log(error);return }

            if (data.count > 0) {
                pager(data.oldest);
            }

        });
    }


}

loadData('annemunition');

d3.json("/api/events/?network=twitch&channel=sledgethewrestler", function(error, data) {

    return;

    console.log( data.data[0]);
    // cast our unix timestamps to local datetimes
    window.eventdata = data.data.map( function(d) { 
        d.datetime = new Date(d.timestamp); 

        d.datetime.setSeconds( 0 );
        d.datetime.setMinutes( d.datetime.getMinutes() - d.datetime.getMinutes() % 5);

        return d
    });

    window.eventnested = d3.nest()
        .key( function (d) { return d.type }) 
        .key( function (d) { return d.datetime })
        .rollup( function (d) { return d.length})
        .entries( window.eventdata);


    // a group per channel we're rendering
    var eventtype = svg.selectAll(".event-type")
        .data(eventnested)
        .enter().append("g")
        .attr("class", "event-type");

    var colors = { 'JOIN':'green', 'PART':'red'}

    // data as a line
    eventtype.append("path")
        .attr("class", "line")
        .attr("d", function(d) { return line(d.values); })
        .style("stroke", function(d) { return colors[d.key]; });

})
