function init() {
    /* set up our SVG element, calc margins, initial scales */

    var margin = {top: 30, right: 30, bottom: 30, left: 50},
        width = window.innerWidth - margin.left - margin.right,  // todo, set width & height based on actual screen size
        height = window.innerHeight - margin.top - margin.bottom - 50;

    var x = d3.scaleTime()
        .domain([new Date(), new Date()])
        .range([0, width]);

    var y = d3.scaleSqrt()
        .range([height, 0]);


    var xAxis = d3.axisBottom()
        .scale(x)

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


    /*
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
            .text("events / m");
    */

}


function render () {

    var canvas = d3.select('svg g#main');

    // Update
    var msgs = canvas
        .selectAll("text")
        .data(updater.msgs)

    msgs
        .transition()
        .duration(500)
        .style("fill", "aliceblue")
        .attr('y', function(d,i) { return (updater.msgs.length - i) +'em'})

    // Create
    msgs.enter().append("text")
        .attr('class', 'chat')
        .attr('x', 0)
        .attr('y', 0)
        .text(function(d) { return d.content; });

    // Remove
    msgs.exit().remove();
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
        render();
    }
};
