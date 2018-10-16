# -*- coding: utf-8 -*-
{
    'name': 'Event Seating',
    'version': '0.1',
    'author': 'Yves Hoyos',
    "license": "AGPL-3",
    'category': 'Event',
    'summary': 'Draw a seating chart for event',
    'depends': [
        'event',
        'event_registration_multi_qty',
        'website',
    ],
    'data': [
        'views/event_view.xml',
        'views/theater_view.xml',
        'views/templates.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
