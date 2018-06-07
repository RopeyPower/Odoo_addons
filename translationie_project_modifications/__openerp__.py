# -*- coding: utf-8 -*-
{
    'name': "translationie_project_modifications",

    'summary': """
        Modifications to the project.project and project.task models for the purpose of modelling translation.ie's workflow
        """,

    'description': """
        Task Modifications:
            Adds Translator, translator deadline and source and target language fields to project.task model.
            Also adds "Create PO" button to task form to allow creation of Purchase orders for tasks.
        Project Modifications:
            Adds Computed fields "Source Languages" and "Target Languages" that auto populate with the languages each task in the project is for.
            Also adds computed fields "translators" and "translator deadlines" that auto populate with the relevant translator information of translators assigned to Translation tasks that belong to the project.
            As well as "reviewers" and "reviewer deadlines" that act the same as the translator fields except for review tasks that belong to the project.
    """,

    'author': "Translation.ie",
    'website': "http://www.translation.ie",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['translationie_respartner_modifications','project','translationie_sale_modifications','web_tree_dynamic_colored_field'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'translationie_project_modifications_view.xml',
        'translationie_respartner_modifications_view.xml',
        'wizard/project_automatic_task_status.xml',
		'wizard/project_task_mark_complete.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}