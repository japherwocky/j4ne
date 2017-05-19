function init() {
    /* set up our SVG element, calc margins, initial scales */

    var margin = {top: 30, right: 30, bottom: 30, left: 50},
        width = window.innerWidth - margin.left - margin.right,  // todo, set width & height based on actual screen size
        height = window.innerHeight - margin.top - margin.bottom - 50;

    window.margin = margin;
    window.height = height;
    window.width = width;


    window.x = d3.scaleTime()
        .domain( [new Date(), new Date()])
        .range([0, (width * 4 / 5)]);

    window.y = d3.scaleLinear()
        .range([height, 0]);

    window.xAxis = d3.axisBottom(x)

    var yAxis = d3.axisLeft()
        .scale(y)

    // add our SVG element
    var svg = d3.select("body").append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)

    // a group with translations for margins
    var maingroup = svg.append("g")
        .attr('id', 'main')
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")")


    // a group for incoming chat msgs
    var chatgroup = maingroup.append('g')
        .attr('id', 'chatgroup')
        .attr("transform", "translate(" + (width * 4 / 5) + ",0)")

    // scatter plot
    maingroup.append('g')
        .attr('id', 'scattergroup')


    // add our axis elements (only one!)
    maingroup.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);

    /*
    maingroup.append("g")
        .attr("class", "y axis")
        .append("text")
            .attr("transform", "rotate(-90)")
            .attr("y", 6)
            .attr("dy", ".71em")
            .style("text-anchor", "end")
            .text("events / m");
    */

    window.render = render_channel;  // choose a default rendering function
}



function render_blue () {

    /* 
        very abstract, clean blue bubbles, 
        global time on the X axis, author ID on Y, 
        chat on the right, sized by message length
    */

    /* resize our axes as required by new data */
    function scale() {

        x.domain(d3.extent(updater.msgs, function(d) {return d.timestamp*1000}))
        d3.select('g.x.axis').call(xAxis)
        y.domain( d3.extent(updater.msgs, function(d) {return d.author_id}))

    }
    scale();  // legacy refactoring junk, this doesn't need to be a function anymore I guess

    var chatbox = d3.select('svg g#chatgroup');

    var msgs = chatbox
        .selectAll("text")
        .data(updater.msgs);


    /* TEXT */

    // Create
    msgs.enter().append("text")
        .attr('class', 'chat')
        .attr('x', 0)
        .attr('y', function(d,i) { return (updater.msgs.length - i) + 'em'})
        .text(function(d) { return d.content; });

    // Update
    msgs
        .attr('y', function(d,i) { return (updater.msgs.length - i) +'em'})
        .transition()
        .duration(500)
        .style("fill", "darkgrey")

    // Remove
    msgs.exit().remove();


    /* DOTS */

    var scats = d3.select('svg g#scattergroup')
        .selectAll('circle')
        .data(updater.msgs)

    // Create
    scats.enter().append('circle')
        .attr('cx', function(d,i) {return x(d.timestamp*1000)})
        .attr('cy', function(d,i) {return y(d.author_id)})
        .attr('r', function(d,i) {return d.content.length})
        .style('fill', 'steelblue')
        .style('fill-opacity', '.6')


    // Update
    scats
        .transition()
            .duration(1000)
            .attr('cx', function(d,i) {return x(d.timestamp*1000)})
            .attr('cy', function(d,i) {return y(d.author_id)})
            .style('fill-opacity', '.2')

    // Remove
    scats.exit().remove()
    
}


function render_channel () {
    /* scatter plot with data bucketed by channel */

    var chatbox = d3.select('svg g#chatgroup');

    var msgs = chatbox
        .selectAll("text")
        .data(updater.msgs)


    /* TEXT */

    // Create
    msgs.enter().append("text")
        .attr('class', 'chat')
        .attr('x', 0)
        .attr('y', function(d,i) { return (updater.msgs.length - i) + 'em'})
        .text(function(d) { return d.content; });

    // Update
    msgs
        .attr('y', function(d,i) { return (updater.msgs.length - i) +'em'})
        .transition()
        .duration(500)
        .style("fill", "darkgrey")

    // Remove
    msgs.exit().remove();


    /* AXES */
    // todo, only compare new data to check extents
    x.domain(d3.extent(updater.msgs, function(d) {return d.timestamp*1000}))
    d3.select('g.x.axis').call(xAxis)


    /* CHANNELS */

    // nest our data by channels we have data for
    var nested = d3.nest().key( function(d) {return d.channel}).entries(updater.msgs);

    // set range of Y axis for the height of one channel
    var chatmargin = (window.height / nested.length) / 6
    // y.domain(d3.extent(updater.msgs, function(d) {return d.author_id}))
    y.domain([0,13])  // modulo author_id by this so we don't have to keep calculating the extents
    y.range([0, (window.height / nested.length) - (chatmargin*2) ])

    /* channel backgrounds */



    /* channel groups */
    var channels = d3.select('svg g#scattergroup')
        .selectAll('.channel')
        .data(nested)


    channels.enter().append('g')
        .attr('data-channel', function (d) {return d.key})
        .attr('class', 'channel')

    channels
        .attr("transform", function(d,i) { return "translate(0," + ((window.height / nested.length) * i) + ")"} )

    channels.exit().remove();

    channels.each( function(d,i) {

        // this = DOM element
        // d = nested data object


        /* TODO: adding these elements only once, but we shouldn't have
            to check - somehow tie into the .append() ?
        */
        // bounding line to divide channels
        var background = d3.select(this).select('line.bounds')

        if (background.empty() == true) {
            // we can't style groups, so throw this in
            d3.select(this).append('line')
                .attr('class', 'bounds')
                .attr('x1', 0)
                .attr('x2', x.range()[1])
                .attr('y1', 0)
                .attr('y2', 0)
                .style('stroke-width', '1px')
                .style('stroke', 'darkgrey')

            d3.select(this).append('text')
                .attr("y", 6)
                .attr("dy", ".71em")
                .style('font-size', '.6em')
                .text(d.key)

        }        

        var scats = d3.select(this)
            .selectAll('circle')
            .data(d.values)

        // Create
        scats.enter().append('circle')
            .attr('cx', function(d,i) { return x(d.timestamp*1000) })
            .attr('cy', function(d,i) { return y(d.author_id % 13) + chatmargin })
            .attr('r', function(d,i) { return Math.log(d.content.length) })
            .style('fill', function(d) { return d.color }) // should be the author's chosen color
            .style('fill-opacity', '1')

        // Update
        scats
            .transition()
                .duration(1000)
                .attr('cx', function(d,i) {return x(d.timestamp*1000)})
                .attr('cy', function(d,i) {return y(d.author_id % 13) + chatmargin })
                .style('fill-opacity', '.6')

        // Remove
        scats.exit().remove()

    })


    /* DOTS 

    var scats = d3.select('svg g#scattergroup')
        .selectAll('circle')
        .data(updater.msgs)

    */ 

}


/* LEGACY TO HANDLE SUBMITTING CHATS */

$(document).ready(function() {
    if (!window.console) window.console = {};
    if (!window.console.log) window.console.log = function() {};

    $("#messageform").live("submit", function() {
        newMessage($(this));
        return false;
    });
    $("#messageform").live("keypress", function(e) {
        if (e.keyCode == 13) {
            newMessage($(this));
            return false;
        }
    });
    $("#message").select();
    updater.start();

    init();

});

function newMessage(form) {
    var message = form.formToDict();
    updater.socket.send(JSON.stringify(message));
    form.find("input[type=text]").val("").select();
}

jQuery.fn.formToDict = function() {
    var fields = this.serializeArray();
    var json = {}
    for (var i = 0; i < fields.length; i++) {
        json[fields[i].name] = fields[i].value;
    }
    if (json.next) delete json.next;
    return json;
};

var updater = {
    socket: null,
    msgs: [],
    buffsize: 1000,

    start: function() {
        var url = "ws://" + location.host + "/chatsocket/";
        updater.socket = new WebSocket(url);
        updater.socket.onmessage = function(event) {
            updater.on_message( JSON.parse(event.data));
        }
    },

    on_message: function(msg) {
        var buffer = updater.msgs;
        buffer.push(msg);
        updater.msgs = buffer.slice(buffer.length-updater.buffsize, buffer.length); // discard oldest items when we hit the cap

        Tstart = new Date()
        render();  // draw things
        // console.log('rendered', updater.msgs.length, 'chats in', (new Date())-Tstart, 'ms');
        
    }
};
