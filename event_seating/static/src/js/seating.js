odoo.define('event_seating.seating', function (require) {
    "use strict";
    var ajax = require('web.ajax');
    var core = require('web.core');
    var _t = core._t;

    var chart, last_selected, selected_seats = [], seat_num = 1, seat_informations = {}, seat_reservation = {};
    var $counter, $cart, $grouped;

    function prepare_seat_informations(registrations) {
        seat_informations = {};
        seat_reservation = {};
        for (var key in registrations) {
            for (var i in registrations[key].seats) {
                var seat = registrations[key].seats[i];
                seat_informations[seat] = registrations[key].name;
                seat_reservation[seat] = key;
            }
        }
    }

    function group_seats(seats) {
        if (jQuery.isEmptyObject(seats)) {
            return [];
        }
        var number_label = {};
        var numbers = [];
        for (var id in seats) {
            var label = seats[id];
            var num = parseInt(label.replace(/\D/g, ""), 10);
            number_label[num] = label;
            numbers.push(num);
        }
        numbers = numbers.sort(function (a, b) { return a - b; });
        var groups = [[number_label[numbers[0]]]];
        var n = 0;
        for (var i=1; i < numbers.length; i++) {
            if (numbers[i-1] + 1 == numbers[i]) {
                groups[n].push(number_label[numbers[i]]);
            }
            else {
                n++;
                groups[n] = [number_label[numbers[i]]];
            }
        }
        return groups;
    }

    function html_group_seats(seats) {
        var groups = group_seats(seats);
        var res = [];
        var n = 0;
        for (var i in groups) {
            if (groups[i].length > 1) {
                var first = groups[i][0];
                var last = groups[i].slice(-1)[0];
                var html = '<span class="label label-success">' + first + '</span> '+
                           '<i class="fa fa-arrows-h" aria-hidden="true"></i> ' +
                           '<span class="label label-success">' + last + '</span>';
                res.push(html);
            }
            else if (groups[i].length == 1) {
                res.push('<span class="label label-success">' + groups[i][0] + '</span>');
            }
        }
        return res.join('<br/>');
    }

    function select_seat(seat) {
        selected_seats[seat.settings.id] = seat.settings.label;
        $('<span class="label label-primary"/>').text(seat.settings.label)
            .attr('id', 'cart-item-' + seat.settings.id)
            .data('seat-id', seat.settings.id)
            .appendTo($cart);
        $cart.append(' ');
    }

    function unselect_seat(seat) {
        delete selected_seats[seat.settings.id];
        $('#cart-item-' + seat.settings.id).remove();
    }

    function book_seat(seat) {
        seat.status('unavailable');
    }

    function unbook_seat(seat) {
        seat.status('available');
    }

    function select_multiple(seat, last_selected_seat, target) {
        var from = $('.seatCharts-seat').index(seat.node());
        var to = $('.seatCharts-seat').index(last_selected_seat.node());
        var start = Math.min(from, to) + 1;
        var end = Math.max(from, to);
        $('.seatCharts-seat').slice(start, end).each(function () {
            var seat = chart.get($(this).attr('id'));
            if (seat.status() != 'unavailable') {
                seat.status(target);
                if (target == 'selected') {
                    select_seat(seat);
                }
                else {
                    unselect_seat(seat);
                }
            }
        });
    }

    function book_multiple(seats_label) {
        for (var i in seats_label) {
            var seat = chart.get(seats_label[i]);
            book_seat(seat);
        }
    }

    function unbook_multiple(seats_label) {
        for (var i in seats_label) {
            var seat = chart.get(seats_label[i]);
            unbook_seat(seat);
        }
    }

    function update_counter_and_seats() {
        $counter.text(Object.keys(selected_seats).length);
        $grouped.html(html_group_seats(selected_seats));
    }

    function add_grp_classes() {
        var grp_num = 0;
        var reservation_grp = [];
        for (var seat in seat_reservation) {
            var reservation_id = seat_reservation[seat];
            if (reservation_grp[reservation_id] === undefined) {
                reservation_grp[reservation_id] = grp_num % 24;
                grp_num++;
            }
            console.log(seat, reservation_grp[reservation_id]);
            $('#' + seat + '.seatCharts-seat').addClass('grp' + reservation_grp[reservation_id]);
        }
    }

    function remove_grp_classes() {
        var grp_num = 0;
        var reservation_grp = [];
        for (var i=0; i<24; i++) {
            $('.seatCharts-seat.grp' + i).removeClass('grp' + i);
        }
    }

    odoo.load_seating_chart = function(with_click, with_assign, with_table) {
        $counter = $('#seats_counter');
        $cart = $('#selected_seats');
        $grouped = $('#selected_grouped_seats');
        var config = {
            map: map,
            seats: seats,
            legend: {
                node: $('#legend'),
                items: legend
            },
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
                $('#seat_informations .seat_number').text(this.settings.label);
                $('#seat_informations .seat_attendee').text(seat_informations[this.settings.label] || '');
                if (this.status() == 'available') {
                    return 'focused';
                }
                return this.style();
            }
        };
        if (with_click) {
            config.click = function (e) {
                if (last_selected && e && e.shiftKey) {
                    var target = this.status() == 'selected' ? 'available' : 'selected';
                    select_multiple(this, last_selected, target);
                }
                last_selected = this;
                if (this.status() == 'available') {
                    select_seat(this);
                    update_counter_and_seats();
                    return 'selected';
                }
                else if (this.status() == 'selected') {
                    unselect_seat(this);
                    update_counter_and_seats();
                    return 'available';
                }
                else if (this.status() == 'unavailable') {
                    return 'unavailable';
                }
                return this.style();
            };
        }
        else {
            config.click = function (e) {
                return this.style();
            };
        }
        chart = $('#seat-map').seatCharts(config);
        if (with_click) {
            $('.unselect_all_seats').on('click', function () {
                chart.find('selected').each(function(seatId) {
                    if (this.status() != 'unavailable') {
                        this.status('available');
                    }
                    unselect_seat(this);
                });
                selected_seats = [];
                $cart.html('');
                $grouped.html('');
                update_counter_and_seats();
                $('#assign').val('');
            });
        }
        if (with_table) {
            if (registrations && !$.isEmptyObject(registrations)) {
                var booked_seats = [];
                for (var key in registrations) {
                    for (var i in registrations[key].seats) {
                        booked_seats.push(registrations[key].seats[i]);
                    }
                }
                book_multiple(Object.values(booked_seats));
                prepare_seat_informations(registrations);
            }
            $('.clear_highlighted_seats').click(function () {
                $('.seatCharts-seat.highlight').removeClass('highlight');
            });
            $('tr.attendee .display').click(function () {
                var registration_id = $(this).closest('tr').data('id');
                var seats = registrations[registration_id].seats;
                $('.seatCharts-seat.highlight').each(function () {
                    var seat = $(this).attr('id');
                    if (jQuery.inArray(seat, seats) == -1) {
                        $(this).removeClass('highlight');
                    }
                });
                chart.get(seats).node().toggleClass('highlight');
                $('#searched_seats').html(html_group_seats(seats) || '');
            });
            $('tr.attendee .select').click(function () {
                $('#assign').val($(this).closest('tr').data('id'));
                if (!$.isEmptyObject(selected_seats)) {
                    $('#validate_assign').click();
                }
            });
            $('tr.attendee .unassign_all').click(function () {
                var registration_id = parseInt($(this).closest('tr').data('id'));
                ajax.jsonRpc('/event_seating/unassign_all_seats', 'call', {
                    registration_id:  registration_id,
                }).then(function (result) {
                    console.log(result);
                    if (result.success) {
                        unbook_multiple(Object.values(registrations[registration_id].seats));
                        registrations[registration_id] = result.registration;
                        var $table_tr = $('#attendees_list .attendee[data-id='+registration_id+']');
                        $table_tr.find('.seats_count').text(result.registration.seats_count);
                        $table_tr.find('.seats_qty').text(result.registration.qty);
                        $('.unselect_all_seats').click();
                        prepare_seat_informations(registrations);
                    }
                    else {
                        alert(result.error);
                    }
                });
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
        if (with_assign) {
            $('#validate_assign').click(function () {
                // Check if selected
                if ($.isEmptyObject(selected_seats)) {
                    alert(_t('Please select seats first.'));
                    return false;
                }
                // Check if attendee
                var registration_value = $('#assign').val();
                var registration_id;
                if (! registration_value) {
                    alert(_t('Please select attendee first.'));
                    return false;
                }
                try {
                    registration_id = parseInt(registration_value);
                }
                catch (exception) {
                    alert(_t('Invalid value for the attendee.'));
                    return false;
                }
                if (isNaN(registration_id)) {
                    alert(_t('Invalid value for the attendee.'));
                    return false;
                }
                // Call ajax
                ajax.jsonRpc('/event_seating/assign_seats', 'call', {
                    registration_id: registration_id,
                    seats: Object.values(selected_seats)
                }).then(function (result) {
                    if (result.success) {
                        registrations[result.registration.id] = result.registration;
                        book_multiple(Object.values(selected_seats));
                        var $table_tr = $('#attendees_list .attendee[data-id='+registration_id+']');
                        $table_tr.find('.seats_count').text(result.registration.seats_count);
                        $table_tr.find('.seats_qty').text(result.registration.qty);
                        $('.unselect_all_seats').click();
                        prepare_seat_informations(registrations);
                    }
                    else {
                        alert(result.error);
                    }
                });
            });
        }
    }
});