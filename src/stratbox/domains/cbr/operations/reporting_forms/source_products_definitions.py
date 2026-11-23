"""Source comparison and readable record metadata."""

from stratbox.operations.declarations import definition as _registry_definition
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.comparison import Comparison
from stratbox.shared.data.representation import Representation
from stratbox.domains.cbr.tables.reporting_forms.contracts import FormFlakes
from stratbox.domains.cbr.tables.reporting_forms.comparison import CompareFormFlakesRequest

COMPARE = _registry_definition('cbr.forms.compare')
READABLE = _registry_definition('cbr.forms.make_readable')
