"""
Pages pakke.
"""

from min_kamp.pages.formation_page import vis_formasjon_side
from min_kamp.pages.kamp_page import vis_kamp_side
from min_kamp.pages.kamptropp_page import vis_kamptropp_side
from min_kamp.pages.login_page import vis_login_side
from min_kamp.pages.oppsett_page import vis_oppsett_side

__all__ = [
    "vis_login_side",
    "vis_kamp_side",
    "vis_kamptropp_side",
    "vis_oppsett_side",
    "vis_formasjon_side",
]
