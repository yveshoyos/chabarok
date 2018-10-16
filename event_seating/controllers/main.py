# -*- coding: utf-8 -*-
from odoo import http, _, tools
from odoo.http import request
from odoo.addons.base.ir.ir_qweb.fields import nl2br
import json


class WebsiteSeatingChart(http.Controller):
    @http.route('/event_seating/preview/<model("event.theater"):theater>', type='http', auth="user", website=True)
    def preview(self, theater, **kwargs):
        return request.render("event_seating.preview", {
            'theater': theater,
        })

    @http.route('/event_seating/<model("event.event"):event>', type='http', auth="user", website=True)
    def set_seats(self, event, **kwargs):
        return request.render("event_seating.seat_selection", {
            'event': event,
            'edit': kwargs.get('edit', False),
        })

    @http.route('/event_seating/assign_seats', type='json', auth="user", website=True)
    def assign_seats(self, registration_id=None, seats=None, **kwargs):
        try:
            print(registration_id)
            print(seats)
            registration = request.env['event.registration'].browse(registration_id)
            registration.assign_seats(seats)
            res = {
                'success': True,
                'registration': registration.get_registration_data()
            }
        except Exception as e:
            request.env.cr.rollback()
            res = {
                'success': False,
                'error': tools.ustr(e),
            }
        return res

    @http.route('/event_seating/unassign_seats', type='json', auth="user", website=True)
    def unassign_seats(self, registration_id=None, seats=None, **kwargs):
        try:
            registration = request.env['event.registration'].browse(registration_id)
            registration.unassign_seats(seats)
            res = {
                'success': True,
                'registration': registration.get_registration_data()
            }
        except Exception as e:
            request.env.cr.rollback()
            res = {
                'success': False,
                'error': tools.ustr(e),
            }
        return res

    @http.route('/event_seating/unassign_all_seats', type='json', auth="user", website=True)
    def unassign_all_seats(self, registration_id=None, **kwargs):
        try:
            registration = request.env['event.registration'].browse(registration_id)
            registration.unassign_all_seats()
            res = {
                'success': True,
                'registration': registration.get_registration_data()
            }
        except Exception as e:
            request.env.cr.rollback()
            res = {
                'success': False,
                'error': tools.ustr(e),
            }
        return res
