# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.http_routing.models.ir_http import slug, slugify
from collections import OrderedDict
import json
import math
import pprint

pp = pprint.PrettyPrinter()

class EventEvent(models.Model):
    _inherit = 'event.event'

    theater_id = fields.Many2one('event.theater', string='Theater')

    def open_website_seating_url(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/event_seating/%s' % slug(self),
            'target': 'self',
        }

    @api.multi
    def get_registrations_json(self):
        self.ensure_one()
        res = {}
        for registration in self.registration_ids:
            res[registration.id] = registration.get_registration_data()
        return json.dumps(res)

    @api.one
    def automatically_compute_seats(self, reset=True):
        if not self.theater_id:
            raise ValidationError(_("You must set a theater before using this function."))
        if len(self.theater_id.seat_ids) < self.seats_expected:
            raise ValidationError(_("There is too much registrations for this theater. Add seats or remove registrations."))
        registrations = self.env['event.registration'].search([('event_id', '=', self.id)], order='date_open')
        if reset:
            for registration in registrations:
                registration.seat_ids.unlink()
        informations = self._auto_compute_prepare_informations(registrations)
        for registration in informations['partial_registrations'] + informations['undone_registrations']:
            seats, informations = self._auto_compute_find_seats(informations, registration)
            informations = self._auto_compute_assign_seats(informations, registration, seats)
        return True

    def _auto_compute_prepare_informations(self, registrations):
        informations = {
            'available_seats': OrderedDict(),
            'booked_seats': OrderedDict(),
            'all_seats': OrderedDict(),
            'done_registrations': [],
            'partial_registrations': [],
            'undone_registrations': [],
            'all_registrations': [],
        }
        for registration in registrations:
            informations['all_registrations'].append(registration)
            if not registration.seat_ids:
                informations['undone_registrations'].append(registration)
            elif len(registration.seat_ids) < registration.qty:
                informations['partial_registrations'].append(registration)
            else:
                informations['done_registrations'].append(registration)
            for seat in registration.seat_ids:
                informations['booked_seats'][seat.label] = seat.seat_id
        for seat in self.theater_id.seat_ids:
            informations['all_seats'][seat.label] = seat
            if seat.label not in informations['booked_seats']:
                informations['available_seats'][seat.label] = seat
        return informations

    def _auto_compute_find_seats(self, informations, registration):
        qty = registration.qty - registration.seats_count
        groups = OrderedDict()
        max_in_subgroup = 0
        subgroup = []
        group_key = False
        # Group by section and by row, then by consecutive seats
        def subgroup_save(grp_key, subgrp):
            if grp_key and subgrp:
                groups[grp_key][(subgrp[0].column, subgrp[-1].column)] = subgrp
                return max(max_in_subgroup, len(subgrp)), [], key
            return max_in_subgroup, [], key
        for seat in informations['available_seats'].values():
            key = (seat.category, seat.row)
            if key not in groups:
                max_in_subgroup, subgroup, group_key = subgroup_save(group_key, subgroup)
                groups[key] = OrderedDict()
            if not subgroup or seat.column == subgroup[-1].column + 1:
                subgroup.append(seat)
            else:
                max_in_subgroup, subgroup, group_key = subgroup_save(group_key, subgroup)
        max_in_subgroup, subgroup, group_key = subgroup_save(group_key, subgroup)
        # Computed to avoid orphan seats
        min_qty_in_reservations = 9999
        for reg in informations['partial_registrations'] + informations['undone_registrations']:
            if registration.id != reg.id:
                min_qty_in_reservations = min(min_qty_in_reservations, reg.qty - reg.seats_count)
        # Check if needed seat can be filled with an other registration
        matching_seats = []
        if qty == max_in_subgroup:
            qty_by_row = qty
        elif qty > max_in_subgroup:
            qty_by_row = max_in_subgroup
        elif max_in_subgroup - min_qty_in_reservations > 0:
            qty_by_row = min(qty, max_in_subgroup - min_qty_in_reservations)
        else:
            qty_by_row = qty
        needed_rows = math.ceil(qty / qty_by_row)
        while needed_rows > 1 and qty_by_row > 0:
            ok = False
            for key, subgroups in groups.items():
                ok = True
                category, row = key
                m = max(map(lambda x: x[1] - x[0] + 1, subgroups.keys()))
                if m < qty_by_row:
                    ok = False
                    continue
                for i in range(1, needed_rows):
                    if (category, row + i) in groups:
                        m = max(map(lambda x: x[1] - x[0] + 1, groups[(category, row + i)].keys()))
                        if m < qty_by_row:
                            ok = False
                            break
                    else:
                        ok = False
                        break
                if ok:
                    break
            if ok:
                break
            else:
                qty_by_row -= 1
                needed_rows = math.ceil(qty / qty_by_row)
        print(registration.name, qty, qty_by_row, needed_rows)
        for key, subgroups in groups.items():
            category, row = key
            for min_max, seats in subgroups.items():
                col_min, col_max = min_max
                n = col_max - col_min + 1
                remaining_qty_on_row = min(qty_by_row, qty - len(matching_seats))
                if remaining_qty_on_row == n or remaining_qty_on_row <= n - min_qty_in_reservations:
                    print('  first row matching, section:', category, 'row:', row)
                    if needed_rows == 1:
                        print('  one row needed => it is OK')
                        matching_seats = seats[:remaining_qty_on_row]
                    else:
                        print('  check following rows')
                        matching_groups = [(category, row, col_min, col_max)]
                        virtual_qty = remaining_qty_on_row
                        for i in range(1, needed_rows):
                            found = False
                            if (category, row + i) in groups:
                                print('    next row is in section:', category, 'row:', row+i)
                                for next_col_min, next_col_max in groups[(category, row + i)].keys():
                                    print('      try with subgroup from', next_col_min, 'to', next_col_max)
                                    if next_col_min <= col_min or next_col_max >= col_max:
                                        print('        subgroup columns are matching')
                                        next_n = next_col_max - next_col_min + 1
                                        next_remaining_qty_on_row = min(qty_by_row, qty - virtual_qty)
                                        if next_remaining_qty_on_row == next_n or next_remaining_qty_on_row <= next_n - min_qty_in_reservations:
                                            print('        OK, there is enough remaining seats')
                                            virtual_qty += next_remaining_qty_on_row
                                            found = True
                                            matching_groups.append((category, row + i, next_col_min, next_col_max))
                                            break
                                        else:
                                            print('        Not enough remaining seats:', next_n, 'asked:', next_remaining_qty_on_row)
                                    else:
                                        print('        subgroup columns are not matching')
                            else:
                                print('    NO next row')
                            if not found:
                                matching_groups = []
                                break
                        for c, r, cmin, cmax in matching_groups:
                            seats = groups[(c, r)][(cmin, cmax)]
                            rem_qty = min(qty_by_row, qty - len(matching_seats))
                            matching_seats += seats[:rem_qty]
                if len(matching_seats) == qty:
                    return matching_seats, informations
        # Too much qty to find consecutive seats => split group
        raise ValidationError(_("Impossible to find seats for registration %s (%s). Try to set seats manually before running the seating algorithm.") % (registration.name, registration.qty))


    def _auto_compute_assign_seats(self, informations, registration, seats):
        seats_label = []
        for seat in seats:
            seats_label.append(seat.label)
            del informations['available_seats'][seat.label]
            informations['booked_seats'][seat.label] = seat
        registration.assign_seats(seats_label)
        if registration in informations['undone_registrations']:
            informations['undone_registrations'].remove(registration)
        if registration in informations['partial_registrations']:
            informations['partial_registrations'].remove(registration)
        if not registration.seat_ids:
            informations['undone_registrations'].append(registration)
        elif len(registration.seat_ids) < registration.qty:
            informations['partial_registrations'].append(registration)
        elif registration not in informations['done_registrations']:
            informations['done_registrations'].append(registration)
        return informations


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    seat_ids = fields.One2many('event.registration.seat', 'registration_id', string='Seats')
    seats_count = fields.Integer(string='Number of seats', compute='_get_seats_count')

    @api.one
    @api.depends('seat_ids', 'seat_ids.registration_id')
    def _get_seats_count(self):
        self.seats_count = len(self.seat_ids)

    @api.multi
    def get_registration_data(self):
        self.ensure_one()
        return  {
            'id': self.id,
            'name': self.name,
            'date': self.date_open,
            'qty': self.qty,
            'seats_count': self.seats_count,
            'seats': [seat.label for seat in self.seat_ids],
        }

    @api.multi
    def assign_seats(self, seats_label):
        self.ensure_one()
        seats = self.env['event.theater.seat'].search([('theater_id', '=', self.event_id.id), ('label', 'in', seats_label)])
        if len(seats_label) != len(seats):
            raise ValidationError(_("Some seats couldn't be found. Please check given labels."))
        for seat in seats:
            self.env['event.registration.seat'].create({
                'registration_id': self.id,
                'seat_id': seat.id
            })
        self.check_seats()

    @api.multi
    def unassign_seats(self, seats_label):
        self.ensure_one()
        seats = self.seat_ids.filtered(lambda r: r.seat_id.label in seats_label)
        if len(seats_label) != len(seats):
            raise ValidationError(_("Some seats couldn't be found. Please check given labels."))
        seats.unlink()

    @api.multi
    def unassign_all_seats(self):
        self.ensure_one()
        self.seat_ids.unlink()

    @api.one
    @api.constrains('seat_ids')
    def check_seats(self):
        if len(self.seat_ids) > self.qty:
            raise ValidationError(_('There is to much assigned seats than booked seats.'))


class EventRegistrationSeat(models.Model):
    _name = 'event.registration.seat'

    registration_id = fields.Many2one('event.registration', string="Registration", required=True)
    event_id = fields.Many2one('event.event', string="Event", related='registration_id.event_id', readonly=True, store=True)
    seat_id = fields.Many2one('event.theater.seat', string='Seat', required=True)
    label = fields.Char(string='Label', related='seat_id.label', readonly=True, store=True)

    @api.one
    @api.constrains('registration_id', 'seat_id')
    def check_disposition_and_names(self):
        if self.registration_id.event_id.theater_id.id != self.seat_id.theater_id.id:
            raise ValidationError(_('Seat is not linked to the same theater than the one in the event.'))

    _sql_constraints = [
        ('unique_seat_event', 'UNIQUE(event_id, seat_id)', 'A seat can only be used once by event'),
    ]
