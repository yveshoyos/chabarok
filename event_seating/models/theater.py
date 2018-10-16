# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.http_routing.models.ir_http import slug, slugify
import json


class EventTheater(models.Model):
    _name = 'event.theater'
    _description = 'Theater'

    name = fields.Char(string='Name', required=True)
    disposition = fields.Text(string='Disposition', required=True)
    seats_names = fields.Text(string='Seats names', required=True, help="Category, relative to seat map. One category per line. Ex: A: Section A")
    colors = fields.Text(string='Colors', help="Colors, relative to seat map. One color (HTML code) per line. Ex: A: #00ff00")
    rows = fields.Selection([('letter', 'Letters'), ('number', 'Numbers')], string='Label on rows', default='letter', required=True)
    display_selected = fields.Selection([('single', 'Single'), ('group', 'Group'), ('both', 'Both')], string='Display selected seats', default='both', required=True)
    seat_ids = fields.One2many('event.theater.seat', 'theater_id', string='Seats')
    active = fields.Boolean(string='Active', default=True)

    @api.multi
    def open_website_url(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/event_seating/preview/%s' % slug(self),
            'target': 'self',
        }

    @api.multi
    def get_json_disposition(self):
        self.ensure_one()
        res = []
        for row in self.disposition.strip().split('\n'):
            res.append(row.strip())
        return json.dumps(res)

    @api.multi
    def _get_seats_name_mapping(self):
        self.ensure_one()
        res = {}
        for line in self.seats_names.split('\n'):
            line = line.strip()
            if line:
                seat, name = list(map(str.strip, line.split(':', 1)))
                res[seat] = {
                    'classes': slugify(name),
                    'category': name,
                }
        return res

    @api.multi
    def _get_seat_colors_mapping(self):
        self.ensure_one()
        res = {}
        if self.colors:
            for line in self.colors.split('\n'):
                line = line.strip()
                if line:
                    seat, color = list(map(str.strip, line.split(':', 1)))
                    res[seat] = color
        return res

    @api.multi
    def get_json_seats(self):
        self.ensure_one()
        return json.dumps(self._get_seats_name_mapping())

    @api.multi
    def get_css_seats_colors(self):
        self.ensure_one()
        classes = self._get_seats_name_mapping()
        colors = self._get_seat_colors_mapping()
        res = ''
        for sear, color in colors.items():
            cl = classes.get(sear, {}).get('classes')
            if cl:
                res += '.seatCharts-seat.available.%s { background-color: %s !important; }\n' % (cl, color)
        return '<style>%s</style>' % res if res else ''

    @api.multi
    def get_json_legend_items(self):
        self.ensure_one()
        res = []
        infos = self._get_seats_name_mapping()
        for seat, info in infos.items():
            res.append([seat, 'available', info['category']])
        res.append(['', 'unavailable', _('Booked')])
        return json.dumps(res)

    @api.multi
    def _get_rows_label(self):
        self.ensure_one()
        rows = self.disposition.strip().split('\n')
        res = range(1, len(rows) + 1, 1)
        if self.rows == 'letter':
            res = [chr(i + 64) for i in res]
        return res

    @api.multi
    def get_rows(self):
        self.ensure_one()
        return json.dumps(self._get_rows_label())

    @api.one
    def create_seats_from_theater(self):
        self.env['event.theater.seat'].search([('theater_id', '=', self.id)]).unlink()
        seat_names = self._get_seats_name_mapping()
        row_labels = self._get_rows_label()
        row = 1
        n = 1
        for line in self.disposition.strip().split('\n'):
            col = 1
            line = line.strip()
            for c in line:
                if c != '_':
                    label = '%s-%s' % (row_labels[row-1], n)
                    self.env['event.theater.seat'].create({
                        'theater_id': self.id,
                        'column': col,
                        'row': row,
                        'character': c,
                        'label': label,
                        'category': seat_names.get(c, {}).get('category', False),
                        'reduced_mobility': col == 1 or col == len(line) or line[col - 2] == '_' or line[col] == '_',
                    })
                    n += 1
                col += 1
            row += 1

    @api.one
    @api.constrains('disposition', 'seats_names')
    def check_disposition_and_names(self):
        row_length = False
        characters = set()
        for line in self.disposition.strip().split('\n'):
            if not row_length:
                row_length = len(line.strip())
            elif len(line.strip()) != row_length:
                raise ValidationError(_('All lines in disposition must have the same length. Use "_" to fill the line.'))
            else:
                for c in line.strip():
                    if c != '_':
                        characters.add(c)
        names = set(self._get_seats_name_mapping().keys())
        for c in characters:
            if c not in names:
                raise ValidationError(_('All used characters in disposition (except "_") must have a seat name.'))

    @api.model
    def create(self, vals):
        record = super(EventTheater, self).create(vals)
        record.create_seats_from_theater()
        return record

    @api.multi
    def write(self, vals):
        res = super(EventTheater, self).write(vals)
        self.create_seats_from_theater()
        return res


class EventTheaterSeat(models.Model):
    _name = 'event.theater.seat'
    _description = 'Theater seat'
    _rec_name = 'label'

    theater_id = fields.Many2one(string='Theaters', required=True, ondelete='cascade')
    column = fields.Integer(string='Column')
    row = fields.Integer(string='Row')
    character = fields.Char(string='Character', size=1)
    label = fields.Char(string='Label', required=True)
    category = fields.Char(string='Category')
    reduced_mobility = fields.Boolean(string='Reduced Mobility')

    def __repr__(self):
        return self.label

    def __str__(self):
        return self.label
