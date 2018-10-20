odoo.define('event_seating.seating', function (require) {
    "use strict";
    var ajax = require('web.ajax');
    var core = require('web.core');
    var _t = core._t;

    var chart, seat_num = 1;

    function add_grp_classes() {
        var grp_num = 0;
        var reservation_grp = [];
        for (var key in registrations) {
            var registration = registrations[key];
            if (reservation_grp[registration.id] === undefined) {
                reservation_grp[registration.id] = grp_num % 24;
                grp_num++;
            }
            for (var i in registration.seats) {
                var seat = registration.seats[i];
                $('#' + seat + '.seatCharts-seat').addClass('grp' + reservation_grp[registration.id]);
            }
        }
    }

    function remove_grp_classes() {
        for (var i=0; i<24; i++) {
            $('.seatCharts-seat.grp' + i).removeClass('grp' + i);
        }
    }

    odoo.load_seating_chart = function(with_click, with_assign, with_table) {
        chart = $('#seat-map').seatCharts({
            map: map,
            seats: seats,
            naming: {
                top: false,
                left: true,
                rows: rows,
                getId: function(character, row, column) {
                    return row + '-' + seat_num;
                },
                getLabel: function (character, row, column) {
                    return row + '-' + seat_num++;
                }
            },
            focus: function (e) {
                return this.style();
            },
            click: function (e) {
                return this.style();
            }
        });
        $('.clear_highlighted_seats').click(function () {
            $('.seatCharts-seat.highlight').removeClass('highlight');
        });
        $('tr.attendee, tr.attendee .display').click(function () {
            var registration_id = $(this).closest('tr').data('id');
            var seats =
            $('.seatCharts-seat.highlight').removeClass('highlight');
            for (var i in registrations[registration_id].seats) {
                $('#'+registrations[registration_id].seats[i]).addClass('highlight');
            }
        });
        $('#reservations_colors').change(function () {
            if ($(this).is(':checked')) {
                add_grp_classes();
            }
            else {
                remove_grp_classes();
            }
        });
    }
});