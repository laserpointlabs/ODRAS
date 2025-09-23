# Reference Ontologies Feature<br>
<br>
This document describes the new reference ontologies feature that allows administrators to create high-level ontologies that can be imported by other projects.<br>
<br>
## Overview<br>
<br>
The reference ontologies feature enables administrators to:<br>
1. Create ontologies marked as "reference ontologies"<br>
2. Import these reference ontologies into any project via the ontology treeview<br>
3. Use reference ontologies as authoritative sources for lower-level projects<br>
<br>
## How It Works<br>
<br>
### For Administrators<br>
<br>
1. **Creating Reference Ontologies**:<br>
   - When creating a new ontology, administrators will see an additional checkbox: "Mark as Reference Ontology (Admin only)"<br>
   - Checking this box creates the ontology as a reference ontology<br>
   - Reference ontologies are stored in the database with `is_reference = TRUE`<br>
<br>
2. **Managing Reference Ontologies**:<br>
   - Reference ontologies appear in the regular ontology list for the project where they were created<br>
   - They can be edited and managed like any other ontology<br>
   - The reference status is maintained in the database<br>
<br>
### For All Users<br>
<br>
1. **Importing Reference Ontologies**:<br>
   - Right-click on the "Imports" node in the ontology treeview<br>
   - Select "Add Reference Ontology" from the context menu<br>
   - A popup will appear showing all available reference ontologies across all projects<br>
   - Click "Import" next to any reference ontology to add it to the current project's imports<br>
<br>
2. **Using Imported Reference Ontologies**:<br>
   - Imported reference ontologies appear under the "Imports" section in the ontology treeview<br>
   - They can be toggled on/off using checkboxes<br>
   - Classes from reference ontologies can be used for equivalence relationships<br>
   - The system automatically matches classes by label for equivalence<br>
<br>
## Technical Implementation<br>
<br>
### Database Changes<br>
<br>
- Added `is_reference` boolean column to `ontologies_registry` table<br>
- Default value is `FALSE`<br>
- Reference ontologies are identified by `is_reference = TRUE`<br>
<br>
### API Endpoints<br>
<br>
- `GET /api/ontologies/reference` - Lists all reference ontologies across all projects<br>
- `POST /api/ontologies` - Enhanced to accept `is_reference` parameter (admin only)<br>
<br>
### Frontend Changes<br>
<br>
- Enhanced ontology creation dialog with reference ontology checkbox (admin only)<br>
- Added right-click context menu to "Imports" node<br>
- Created reference ontology selector popup<br>
- Integrated with existing import/overlay system<br>
<br>
## Database Migration<br>
<br>
If you have an existing database, run the migration script:<br>
<br>
```bash<br>
psql -d odras -f scripts/migrate_add_reference_ontologies.sql<br>
```<br>
<br>
## Testing<br>
<br>
Run the test script to verify the functionality:<br>
<br>
```bash<br>
python test_reference_ontologies.py<br>
```<br>
<br>
## Security Considerations<br>
<br>
- Only users with `is_admin = TRUE` can create reference ontologies<br>
- The API endpoint for listing reference ontologies is available to all authenticated users<br>
- Reference ontologies can be imported by any user into any project they have access to<br>
<br>
## Use Cases<br>
<br>
1. **Domain-Specific Standards**: Create reference ontologies for industry standards or domain-specific vocabularies<br>
2. **Common Vocabularies**: Establish common terms and concepts that multiple projects should use<br>
3. **Authority Sources**: Provide authoritative definitions that lower-level projects can reference<br>
4. **Consistency**: Ensure consistent terminology across multiple projects<br>
<br>
## Future Enhancements<br>
<br>
Potential future improvements could include:<br>
- Versioning of reference ontologies<br>
- Approval workflows for reference ontology changes<br>
- Usage tracking to see which projects import which reference ontologies<br>
- Automatic updates when reference ontologies change<br>

