frappe.ui.form.on("Task", {
	refresh(frm) {
		// coloured banner with the compliance traffic light (only on compliance obligations)
		const status = frm.doc.custom_compliance_status;
		if (!status) return;
		const colors = {
			"On Track": "green",
			"At Risk": "orange",
			Overdue: "red",
			"Completed On Time": "blue",
			"Completed Late": "yellow",
		};
		frm.dashboard.set_headline_alert(`${__("Compliance Status")}: <b>${__(status)}</b>`, colors[status]);
	},
});
