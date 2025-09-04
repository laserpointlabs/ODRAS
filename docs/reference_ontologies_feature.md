# Reference Ontologies Feature

This document describes the new reference ontologies feature that allows administrators to create high-level ontologies that can be imported by other projects.

## Overview

The reference ontologies feature enables administrators to:
1. Create ontologies marked as "reference ontologies"
2. Import these reference ontologies into any project via the ontology treeview
3. Use reference ontologies as authoritative sources for lower-level projects

## How It Works

### For Administrators

1. **Creating Reference Ontologies**:
   - When creating a new ontology, administrators will see an additional checkbox: "Mark as Reference Ontology (Admin only)"
   - Checking this box creates the ontology as a reference ontology
   - Reference ontologies are stored in the database with `is_reference = TRUE`

2. **Managing Reference Ontologies**:
   - Reference ontologies appear in the regular ontology list for the project where they were created
   - They can be edited and managed like any other ontology
   - The reference status is maintained in the database

### For All Users

1. **Importing Reference Ontologies**:
   - Right-click on the "Imports" node in the ontology treeview
   - Select "Add Reference Ontology" from the context menu
   - A popup will appear showing all available reference ontologies across all projects
   - Click "Import" next to any reference ontology to add it to the current project's imports

2. **Using Imported Reference Ontologies**:
   - Imported reference ontologies appear under the "Imports" section in the ontology treeview
   - They can be toggled on/off using checkboxes
   - Classes from reference ontologies can be used for equivalence relationships
   - The system automatically matches classes by label for equivalence

## Technical Implementation

### Database Changes

- Added `is_reference` boolean column to `ontologies_registry` table
- Default value is `FALSE`
- Reference ontologies are identified by `is_reference = TRUE`

### API Endpoints

- `GET /api/ontologies/reference` - Lists all reference ontologies across all projects
- `POST /api/ontologies` - Enhanced to accept `is_reference` parameter (admin only)

### Frontend Changes

- Enhanced ontology creation dialog with reference ontology checkbox (admin only)
- Added right-click context menu to "Imports" node
- Created reference ontology selector popup
- Integrated with existing import/overlay system

## Database Migration

If you have an existing database, run the migration script:

```bash
psql -d odras -f scripts/migrate_add_reference_ontologies.sql
```

## Testing

Run the test script to verify the functionality:

```bash
python test_reference_ontologies.py
```

## Security Considerations

- Only users with `is_admin = TRUE` can create reference ontologies
- The API endpoint for listing reference ontologies is available to all authenticated users
- Reference ontologies can be imported by any user into any project they have access to

## Use Cases

1. **Domain-Specific Standards**: Create reference ontologies for industry standards or domain-specific vocabularies
2. **Common Vocabularies**: Establish common terms and concepts that multiple projects should use
3. **Authority Sources**: Provide authoritative definitions that lower-level projects can reference
4. **Consistency**: Ensure consistent terminology across multiple projects

## Future Enhancements

Potential future improvements could include:
- Versioning of reference ontologies
- Approval workflows for reference ontology changes
- Usage tracking to see which projects import which reference ontologies
- Automatic updates when reference ontologies change
