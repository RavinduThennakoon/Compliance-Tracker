app_name = "compliance_tracker"
app_title = "Compliance Tracker"
app_publisher = "Ravindu Thennakoon"
app_description = "CRM-driven automated compliance and workflow tracking for audit and tax advisory firms"
app_email = "tennakoonravindu79@gmail.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "compliance_tracker",
# 		"logo": "/assets/compliance_tracker/logo.png",
# 		"title": "Compliance Tracker",
# 		"route": "/compliance_tracker",
# 		"has_permission": "compliance_tracker.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/compliance_tracker/css/compliance_tracker.css"
# app_include_js = "/assets/compliance_tracker/js/compliance_tracker.js"

# include js, css files in header of web template
# web_include_css = "/assets/compliance_tracker/css/compliance_tracker.css"
# web_include_js = "/assets/compliance_tracker/js/compliance_tracker.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "compliance_tracker/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
		"Customer": "public/js/customer.js",
		"Task": "public/js/task.js",
 		"Projects Settings": "public/js/projects_settings.js",}
doctype_list_js = {"Task": "public/js/task_list.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "compliance_tracker/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"
# Client portal: menu entry and landing page for ERPNext's standard "Customer" role
standard_portal_menu_items = [
	{"title": "My Compliance", "route": "/my-compliance", "role": "Customer"},
]
role_home_page = {"Customer": "my-compliance"}


# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "compliance_tracker.utils.jinja_methods",
# 	"filters": "compliance_tracker.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "compliance_tracker.install.before_install"
# after_install = "compliance_tracker.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "compliance_tracker.uninstall.before_uninstall"
# after_uninstall = "compliance_tracker.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "compliance_tracker.utils.before_app_install"
# after_app_install = "compliance_tracker.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "compliance_tracker.utils.before_app_uninstall"
# after_app_uninstall = "compliance_tracker.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "compliance_tracker.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "compliance_tracker.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
	"Customer": {
		"validate": "compliance_tracker.events.customer.validate",
	},
    "Projects Settings": {
		"validate": "compliance_tracker.events.projects_settings.validate",
	},
    "Task": {
		"validate": "compliance_tracker.events.task.validate",
	},
}
scheduler_events = {
	"cron": {
		# every 15 minutes; runs the compliance engine once a day after Projects Settings > Daily Run Time
		"*/15 * * * *": ["compliance_tracker.scheduler.run_if_due"],
	},
}


# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"compliance_tracker.tasks.all"
# 	],
# 	"daily": [
# 		"compliance_tracker.tasks.daily"
# 	],
# 	"hourly": [
# 		"compliance_tracker.tasks.hourly"
# 	],
# 	"weekly": [
# 		"compliance_tracker.tasks.weekly"
# 	],
# 	"monthly": [
# 		"compliance_tracker.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "compliance_tracker.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "compliance_tracker.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "compliance_tracker.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "compliance_tracker.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["compliance_tracker.utils.before_request"]
# after_request = ["compliance_tracker.utils.after_request"]

# Job Events
# ----------
# before_job = ["compliance_tracker.utils.before_job"]
# after_job = ["compliance_tracker.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"compliance_tracker.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# --- Compliance Tracker: installation ---------------------------------------
after_install = "compliance_tracker.install.after_install"
after_migrate = "compliance_tracker.install.after_migrate"
