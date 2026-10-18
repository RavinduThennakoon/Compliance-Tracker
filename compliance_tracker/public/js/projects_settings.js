frappe.ui.form.on("Projects Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Run Compliance Engine Now"), () => {
			frappe.call({
				method: "compliance_tracker.scheduler.run_now",
				freeze: true,
				freeze_message: __("Generating obligations and sending reminders..."),
				callback: (r) => {
					frappe.msgprint(r.message, __("Compliance Engine"));
					frm.reload_doc();
				},
			});
		});
	},
});
