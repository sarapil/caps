# Copyright (c) 2024, Moataz M Hassan (Arkan Lab)
# Developer Website: https://arkan.it.com
# License: MIT
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Capability(Document):
    def autoname(self):
        self.name = self.name1

    def validate(self):
        self._validate_name_format()
        self._validate_prerequisites()

    def _validate_name_format(self):
        if not self.name1:
            return
        parts = self.name1.split(":")
        if len(parts) < 2:
            frappe.throw(
                "Capability name must follow the format "
                "{category}:{scope_doctype}:{scope_field_or_action}"
            )

    def _validate_prerequisites(self):
        """Validate no self-references or circular dependency chains."""
        if not self.prerequisites:
            return

        seen = set()
        for row in self.prerequisites:
            if row.prerequisite == self.name:
                frappe.throw(
                    f"Capability cannot be a prerequisite of itself: {self.name}"
                )
            if row.prerequisite in seen:
                frappe.throw(
                    f"Duplicate prerequisite: {row.prerequisite}"
                )
            seen.add(row.prerequisite)

        # Check for circular dependencies (BFS)
        self._check_circular_deps(seen)

    def _check_circular_deps(self, direct_prereqs: set):
        """BFS through the prerequisite graph to detect cycles back to self."""
        visited = set()
        queue = list(direct_prereqs)

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # Get prerequisites of this capability
            child_prereqs = frappe.get_all(
                "Capability Prerequisite",
                filters={"parent": current, "parenttype": "Capability"},
                pluck="prerequisite",
            )
            for cp in child_prereqs:
                if cp == self.name:
                    frappe.throw(
                        f"Circular dependency detected: {self.name} → ... → {current} → {self.name}"
                    )
                if cp not in visited:
                    queue.append(cp)
