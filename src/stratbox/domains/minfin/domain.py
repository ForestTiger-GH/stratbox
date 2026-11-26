"""The thirteen fiscal series have one explicit static catalog."""
from stratbox.capabilities.model.domains import DomainSpec
from .common.access import ACCESS
from .series.federal_budget import FED_MONTHLY, FED_QUARTERLY, FED_ANNUAL
from .series.consolidated_budget import CON_MONTHLY, CON_QUARTERLY, CON_ANNUAL
from .series.regional_budgets import SUB_MONTHLY, SUB_QUARTERLY, SUB_ANNUAL
from .series.fund_movement import FUND_MOVEMENT
from .series.fund_volume import FUND_VOLUME
from .series.fund_shares import FUND_SHARES
from .series.fund_deposits import FUND_DEPOSITS
from .calculations.budget import BUDGET_CHANGES, BUDGET_PERIOD_FLOWS, BUDGET_RATIOS
from .calculations.fund import FUND_LIQUID_ASSETS, FUND_CHANGES
from .products.specifications import BUDGET_OVERVIEW, FUND_OVERVIEW

DOMAIN = DomainSpec(
    id="minfin",
    common={ACCESS.id: ACCESS},
    series={
        FED_MONTHLY.id: FED_MONTHLY,
        FED_QUARTERLY.id: FED_QUARTERLY,
        FED_ANNUAL.id: FED_ANNUAL,
        CON_MONTHLY.id: CON_MONTHLY,
        CON_QUARTERLY.id: CON_QUARTERLY,
        CON_ANNUAL.id: CON_ANNUAL,
        SUB_MONTHLY.id: SUB_MONTHLY,
        SUB_QUARTERLY.id: SUB_QUARTERLY,
        SUB_ANNUAL.id: SUB_ANNUAL,
        FUND_MOVEMENT.id: FUND_MOVEMENT,
        FUND_VOLUME.id: FUND_VOLUME,
        FUND_SHARES.id: FUND_SHARES,
        FUND_DEPOSITS.id: FUND_DEPOSITS
    },
    calculations={BUDGET_CHANGES.id: BUDGET_CHANGES, BUDGET_PERIOD_FLOWS.id: BUDGET_PERIOD_FLOWS,
                  BUDGET_RATIOS.id: BUDGET_RATIOS, FUND_LIQUID_ASSETS.id: FUND_LIQUID_ASSETS,
                  FUND_CHANGES.id: FUND_CHANGES},
    products={BUDGET_OVERVIEW.id: BUDGET_OVERVIEW, FUND_OVERVIEW.id: FUND_OVERVIEW},
)
