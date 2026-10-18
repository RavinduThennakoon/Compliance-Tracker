frappe.query_reports["Compliance Status Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("Due From"),
			fieldtype: "Date",
			default: frappe.datetime.year_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("Due To"),
			fieldtype: "Date",
			default: frappe.datetime.year_end(),
			reqd: 1,
		},
		{ fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer" },
		{
			fieldname: "service",
			label: __("Service"),
			fieldtype: "Link",
			options: "Item",
			get_query: () => ({ filters: { item_group: "Statutory Services" } }),
		},
		{
			fieldname: "compliance_status",
			label: __("Compliance Status"),
			fieldtype: "Select",
			options: ["", "On Track", "At Risk", "Overdue", "Completed On Time", "Completed Late"],
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "compliance_status" && data && data.compliance_status) {
			const colors = {
				"On Track": "green",
				"At Risk": "orange",
				Overdue: "red",
				"Completed On Time": "blue",
				"Completed Late": "yellow",
			};
			value = `<span class="indicator-pill ${colors[data.compliance_status] || "gray"}">${value}</span>`;
		}
		return value;
	},
};
