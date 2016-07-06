var margin = {top: 20, right: 80, bottom: 30, left: 50},
    width = window.innerWidth - margin.left - margin.right,  // todo, set width & height based on actual screen size
    height = window.innerHeight - margin.top - margin.bottom;

var x = d3.time.scale()
    .domain([new Date(), new Date()])
    .range([0, width]);

var y = d3.scale.sqrt()
    .range([height, 0]);

var color = d3.scale.category10();

var xAxis = d3.svg.axis()
    .scale(x)
    .orient("bottom");

var yAxis = d3.svg.axis()
    .scale(y)
    .orient("left");

var line = d3.svg.line()
    // .interpolate("basis")
    .x(function(d) { return x(new Date(d.key)); })
    .y(function(d) { return y(d.values); });


function mkzoom() {
    var xzoom = d3.behavior.zoom()
        .x(x)
        .on('zoom', function () {
            updateBarsize();
            renderMessages();
            renderEvents();
        })
    svg.call(xzoom);
    }

// add our SVG element
var svg = d3.select("body").append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)

// a group with translations for margins
var maingroup = svg.append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")")


// add our axis elements (only one!)
maingroup.append("g")
    .attr("class", "x axis")
    .attr("transform", "translate(0," + height + ")")

maingroup.append("g")
    .attr("class", "y axis")
    .append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", 6)
        .attr("dy", ".71em")
        .style("text-anchor", "end")
        .text("Chat / 10m");

// a group for our chat data
var chatgroup = maingroup.append("g")
    .attr("class", "chat");

var eventgroup = maingroup.append("g")
    .attr("class", "events");


function updateAxes(dataset) {
    var existing = x.domain();
    var updated = d3.extent(dataset, function(d) {return new Date(d.datetime)});

    x.domain( [ d3.min([existing[0], updated[0]]),
                d3.max([existing[1], updated[1]]),
                ]
            )

    // we set the Y values in the rendering loop, where we nest the data
    // TODO don't

    updateBarsize();

    }

function updateBarsize() {

    // calculate the width of one tick
    var xdomain = x.domain();
    var xticks = (xdomain[1] - xdomain[0]) / 60 / 5 / 1000;  // number of 10 minute ticks on the chart
    var barwidth = (width / xticks) - 2;
    window.barwidth = barwidth < 1 ? 1 : barwidth;

}


/* RENDER MESSAGE DATA */
function renderMessages() {

    // nest our data by channel and datetime (our data loader has bucketed this already)
    var nested = d3.nest()
        .key( function (d) { return d.datetime })
        .rollup( function (d) { return d.length})
        .entries( window.rawdata.messages);


    y.domain([
        0,
        d3.max(nested, function(d) {return d.values})
        ])

    

    svg.select('g.x.axis')
        .call(xAxis);

    svg.select('g.y.axis')
        .call(yAxis)

    var bars = chatgroup.selectAll('.messagebar')
        .data(nested)

    bars
        .enter()
        .append("rect")
        .attr('class', 'messagebar')

    bars
        .attr('x', function(d) {return x(new Date(d.key))})
        .attr('y', function(d) {return y(d.values)})
        .attr('width', barwidth)
        .attr('height', function(d) {return height - y(d.values)})

    }

function renderEvents() {

    window.eventnested = d3.nest()
        .key( function (d) { return d.type }) 
        .key( function (d) { return d.datetime })
        .rollup( function (d) { return d.length})
        .entries( window.rawdata.events);

    var colors = { 'JOIN':'green', 'PART':'red', 'SUB':'orange', 'TIMEOUT':'yellow'}

    // a group per type of event
    var eventtype = eventgroup.selectAll(".event-type")
        .data(eventnested)

    eventtype
        .enter().append("g")
        .attr("class", "event-type");

    var eventwidth = (barwidth / eventnested.length) - 2;
    eventwidth = eventwidth < 1 ? 1 : eventwidth;

    eventtype.each( function(d, i, set) {
        var color = colors[d.key];

        var bars = d3.select(this).selectAll('.eventbar')
            .data(d.values)

        bars
            .enter()
            .append('rect')
            .attr('class', 'eventbar')

        bars
            .attr('x', function(d) {return x(new Date(d.key)) + (eventwidth*i) + 2  })
            .attr('y', function(d) {return y(d.values)})
            .attr('width', eventwidth)
            .attr('height', function(d) {return height - y(d.values)})
            .attr('opacity', '.6')
            .attr('fill', color)

    })

    /*
    // data as a line
    eventtype.append("path")
        .attr("class", "line")
        .style("stroke", function(d) { return colors[d.key] });

    eventtype.select('.line')
        .attr("d", function(d) {return line(d.values) });
    */

}


function loadData(channel, type) {

    // recursively load all back data
    var now = moment.utc().toISOString(),
        apipath = 'api/'+type+'/?network=twitch&channel=';

    apipath += channel;

    pager(now);

    function pager(oldest) {
        var thispath = apipath + '&before='+oldest;
        d3.json(thispath, function(error, data) {

            if (error) { console.log(error);return }

            if (data.count > 0) {
                pager(data.oldest);
            } else {
                // when all is loaded, set up our zooming
                mkzoom();
            }

            // concat and transform our data set

            // cast our unix timestamps to local datetimes
            Tdata = data.data.map( function(d) { 
                d.datetime = type == 'messages' ? new Date(d.timestamp * 1000) : new Date(d.timestamp);  // glorious
                d.datetime.setSeconds( 0 );
                // TODO: use a threshold scale instead of rounding timestamps
                d.datetime.setMinutes( d.datetime.getMinutes() - d.datetime.getMinutes() % 5);
                return d
                });

            window.rawdata[type] = window.rawdata[type].concat(Tdata);

            // render our data
            updateAxes(window.rawdata[type]);
            renderMessages();
            renderEvents();


        });
    }


}

window.rawdata = {'events':[], 'messages':[]}

loadData('sledgethewrestler', 'messages');
loadData('sledgethewrestler', 'events');

