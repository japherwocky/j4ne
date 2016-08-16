function init() {
    /* set up our SVG element, calc margins, initial scales */

    var margin = {top: 30, right: 30, bottom: 30, left: 50},
        width = window.innerWidth - margin.left - margin.right,  // todo, set width & height based on actual screen size
        height = window.innerHeight - margin.top - margin.bottom - 50;

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

}


function scale() {
    x.domain(d3.extent(updater.msgs, function(d) {return d.timestamp*1000}))

    d3.select('g.x.axis').call(xAxis)

    y.domain( d3.extent(updater.msgs, function(d) {return d.author_id}))

}


function render () {

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

    start: function() {
        var url = "ws://" + location.host + "/chatsocket";
        updater.socket = new WebSocket(url);
        updater.socket.onmessage = function(event) {
            updater.on_message( JSON.parse(event.data));
        }
    },

    on_message: function(msg) {
        updater.msgs.push(msg);
        scale(); 
        render();
    }
};
