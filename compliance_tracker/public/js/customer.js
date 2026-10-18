frappe.ui.form.on("Customer", {
	setup(frm) {
		// only statutory service Items can be picked in the Compliance tab
		frm.set_query("service", "custom_compliance_services", () => ({
			filters: { item_group: "Statutory Services", disabled: 0 },
		}));
	},
	refresh(frm) {
		if (frm.is_new() || !(frm.doc.custom_compliance_services || []).length) return;
		frm.add_custom_button(__("Generate Obligations Now"), () => {
			frappe.call({
				method: "compliance_tracker.generation.generate_now",
				args: { customer: frm.doc.name },
				freeze: true,
				callback: (r) => {
					frappe.show_alert({ message: __("{0} obligation(s) created", [r.message]), indicator: "green" });
					frappe.set_route("List", "Task", { custom_customer: frm.doc.name });
				},
			});
		}, __("Compliance"));
	},
});

frappe.ui.form.on("Customer Compliance Service", {
	service(frm, cdt, cdn) {
		// copy the Item's default rule; staff can still change it for this customer
		const row = locals[cdt][cdn];
		if (!row.service) return;
		frappe.db
			.get_value("Item", row.service, [
				"custom_filing_frequency",
				"custom_due_day",
				"custom_months_after_period_end",
			])
			.then(({ message: item }) => {
				frappe.model.set_value(cdt, cdn, {
					frequency: item.custom_filing_frequency,
					due_day: item.custom_due_day,
					months_after_period_end: item.custom_months_after_period_end,
				});
			});
	},
});
