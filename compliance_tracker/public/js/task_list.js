// Adds compliance colours to ERPNext's Task list without replacing ERPNext's own list settings
(() => {
	const colors = {
		"On Track": "green",
		"At Risk": "orange",
		Overdue: "red",
		"Completed On Time": "blue",
		"Completed Late": "yellow",
	};
	const settings = (frappe.listview_settings["Task"] = frappe.listview_settings["Task"] || {});
	settings.formatters = Object.assign(settings.formatters || {}, {
		custom_compliance_status(value) {
			if (!value) return "";
			return `<span class="indicator-pill ${colors[value] || "gray"}">${__(value)}</span>`;
		},
	});
})();
