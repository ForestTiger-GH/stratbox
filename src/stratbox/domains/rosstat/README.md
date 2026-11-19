# Rosstat

The package groups official Rosstat domains by publisher. It does not register
operations itself. The owner rosstat.publications manages source landing
pages, publisher issues, attachment identities, and exact original acquisition.

Future Rosstat statistical parsers, derived tables and series-local
representations will live in neighboring source-family packages. Their
business and classification rules must not be embedded in the common
publication downloader.

The initial HTML source profiles are provisional. The four official landing
pages are fixed, but real current markup, attachments, delivery hosts and
possible JavaScript publication catalogs require live calibration. Until
then synthetic HTML tests establish offline API behavior, not live availability.
The source may be unavailable: 404, 502 and timeout do not signify no updates.

See publications/README.md.
