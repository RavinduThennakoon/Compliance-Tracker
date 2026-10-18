frappe.ui.form.on("Customer", {
	setup(frm) {
		// only statutory service Items can be picked in the Compliance tab
		frm.set_query("service", "custom_compliance_services", () => ({
			filters: { item_group: "Statutory Services", disabled: 0 },
		}));
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
