# -*- encoding: utf-8 -*-
from openerp.osv import osv, fields
from openerp.tools.safe_eval import safe_eval


def clean_name(name):
    import re
    exp = r'\[.*?\]'
    text = name.strip()
    found = re.findall(exp, text)
    if found:
        for f in found:
            text = text.replace(f, '').strip()
    words = text.split(' ')
    if len(words) > 2:
        text = ' '.join([words[0], words[2]])
    return text


class fiscal_book_wizard(osv.osv_memory):

    _name = "hr.timesheet.reports.base"
    _rec_name = 'filter_id'

    def _prepare_data(self, record):
        return {'author': clean_name(record.user_id.name),
                'description': record.name,
                'duration': record.unit_amount,
                'date': record.date,
                'analytic': record.account_id.name,
                'id': record.id,
                }

    def _get_print_data(self, cr, uid, ids, name, args, context=None):
        res = {}
        for wzd in self.browse(cr, uid, ids, context=context):
            res[wzd.id] = self._get_result_ids(cr, uid, ids, context=context)
        return res

    def _get_result_ids(self, cr, uid, ids, context=None):
        res = []
        wzr_brw = self.browse(cr, uid, ids, context=context)[0]
        domain = wzr_brw.filter_id.domain
        domain_inv = wzr_brw.filter_invoice_id.domain
        timesheet_obj = self.pool.get('hr.analytic.timesheet')
        invoice_obj = self.pool.get('account.invoice')
        dom = [len(d) > 1 and tuple(d) or d for d in safe_eval(domain)]
        dom_inv = [len(d) > 1 and tuple(d) or d for d in safe_eval(domain_inv)]
        timesheet_ids = timesheet_obj.search(cr, uid, dom,
                                             order='account_id asc, user_id asc, date asc',  # noqa
                                             context=context)
        # Group elements
        timesheet_brws = timesheet_obj.browse(cr, uid, timesheet_ids,
                                              context=context)
        res = [self._prepare_data(tb) for tb in timesheet_brws]
        grouped = timesheet_obj.read_group(cr, uid, dom,
                                           ['account_id', 'unit_amount'],
                                           ['account_id'],
                                           context=context)
        grouped_month = timesheet_obj.read_group(cr, uid, dom,
                                                 ['date',
                                                  'account_id',
                                                  'unit_amount'],
                                                 ['date'],
                                                 context=context)
        grouped_invoices = invoice_obj.read_group(cr, uid, dom_inv,
                                                  ['currency_id',
                                                   'date_invoice',
                                                   'partner_id',
                                                   'amount_total'],
                                                  ['currency_id',
                                                   'date_invoice',
                                                   'partner_id'],
                                                  context=context)
        print grouped_invoices
        # Separate per project (analytic)
        projects = set([l['analytic'] for l in res])
        info = {
            'data': {},
            'resume': grouped,
            'resume_month': grouped_month,
            'invoices': grouped_invoices,
        }
        for proj in projects:
            info['data'][proj] = [r for r in res if r['analytic'] == proj]
        return info

    _columns = {
        'filter_invoice_id': fields.many2one(
            'ir.filters', 'Invoices',
            domain=[('model_id', 'ilike', 'account.invoice')],
            help='Filter of Invoices to be shown TIP: '
            'Go to Accounting/Customer '
            'Invoices in order to create the filter you want to show on this'
            'report.',),
        'filter_id': fields.many2one(
            'ir.filters', 'Filter',
            domain=[('model_id', 'ilike', 'hr.analytic.timesheet')],
            help="Filter should be by date, group_by is ignored, the model "
            "which the filter should belong to is timesheet."),
        'records': fields.function(_get_print_data,
                                   string='Records', type="text")
    }

    def do_report(self, cr, uid, ids, context=None):
        return {'type': 'ir.actions.report.xml',
                'name': 'hr.timesheet.reports.explain',
                'report_name': 'hr.timesheet.reports.base',
                'report_type': "webkit",
                'string': "Hr timesheet reports base",
                'file': "hr_timesheet_reports/wizard/hr_timesheet_reports_base.mako",  # noqa
                'nodestroy': True,
                }
