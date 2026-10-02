"""Predefined complaint reason categories.

The raw list supplied by the business repeated some categories; the repeat count
is used here as a relative frequency weight.
"""

# category -> relative weight (from repeat count in the source list)
REASON_WEIGHTS = {
    "Color - Fade": 1,
    "Adhesion": 4,
    "Alkalinity": 1,
    "Application": 11,
    "Blocking": 1,
    "Burnishing": 1,
    "Chalking": 1,
    "Flashing": 1,
    "Foam": 2,
    "Gassing": 1,
    "Gelled": 1,
    "Gloss and Sheen": 3,
    "Gloss Fade": 1,
    "Hide": 1,
    "Mildew": 1,
    "Odor": 1,
    "Package": 4,
    "Product Satisfaction Guarantee": 1,
    "Service Satisfaction Guarantee": 2,
    "Scrubbability": 1,
    "Settling": 1,
    "Skinning": 1,
}

REASONS = list(REASON_WEIGHTS)

# Natural-language comment templates per reason, used to build synthetic text.
COMMENT_TEMPLATES = {
    "Color - Fade": [
        "Color faded badly on the south facing wall after only {months} months.",
        "Customer says the {color} has gone dull and washed out compared to the sample.",
        "Exterior color shifted noticeably within one season.",
    ],
    "Adhesion": [
        "Paint is peeling off the {substrate} in sheets, no adhesion at all.",
        "Coating lifted when the tape was removed from the {substrate}.",
        "Product would not bond to the primed {substrate}; flaking within {months} months.",
    ],
    "Alkalinity": [
        "Burn-through on new masonry, customer suspects alkalinity attack.",
        "Color burned and blotchy over fresh concrete block.",
    ],
    "Application": [
        "Product dragged badly under the roller and would not lay off smooth.",
        "Sprayed poorly, heavy spitting at the tip even after thinning.",
        "Brush marks will not level out, finish looks streaky.",
        "Way too thick out of the can, painter had to fight it the whole job.",
        "Set up too fast in {temp}F weather, impossible to keep a wet edge.",
        "Roller stipple is much heavier than the customer expected.",
    ],
    "Blocking": [
        "Door stuck to the jamb and pulled the film off after {days} days of cure.",
        "Trim tacked up and blocked when windows were closed overnight.",
    ],
    "Burnishing": [
        "Wall shines wherever it is touched or rubbed in the hallway.",
        "Burnishing showing along the corridor at hand height.",
    ],
    "Chalking": [
        "Heavy chalk rubbing off on hands after {months} months outdoors.",
        "White chalky residue all over the siding and the customer's clothes.",
    ],
    "Flashing": [
        "Patched areas flashed through the topcoat, spotty sheen everywhere.",
        "Flashing over the drywall repairs even with two full coats.",
    ],
    "Foam": [
        "Excessive foam during roll application left craters in the film.",
        "Product foamed up when boxed, bubbles dried into the surface.",
    ],
    "Gassing": [
        "Can was bulging on the shelf, appears to be gassing.",
        "Lid popped off the pail, contents had gassed up in storage.",
    ],
    "Gelled": [
        "Contents were gelled solid when the can was opened.",
        "Product had thickened to pudding consistency, unusable.",
    ],
    "Gloss and Sheen": [
        "Sheen is far flatter than the {sheen} stated on the label.",
        "Uneven sheen across the wall, patchy shiny and dull areas.",
        "Gloss level does not match the previous order of the same product.",
    ],
    "Gloss Fade": [
        "Gloss dropped off within {months} months on the exterior door.",
        "Finish lost its shine much faster than expected.",
    ],
    "Hide": [
        "Took four coats and still not covering the old {color} color.",
        "Poor hide over the primer, shadowing still visible.",
    ],
    "Mildew": [
        "Mildew growing on the ceiling within {months} months of painting.",
        "Black spotting returned on the bathroom walls very quickly.",
    ],
    "Odor": [
        "Strong lingering odor in the bedroom days after painting.",
        "Customer reports a sour smell coming from the dried film.",
    ],
    "Package": [
        "Can arrived dented and leaking on the pallet.",
        "Label on the pail did not match the product inside.",
        "Lid was not sealed, product had skinned in shipment.",
        "Pail handle broke off when lifted, spilled product.",
    ],
    "Product Satisfaction Guarantee": [
        "Customer unhappy with overall results and requesting a refund under the guarantee.",
        "Requesting replacement product under the satisfaction guarantee.",
    ],
    "Service Satisfaction Guarantee": [
        "Order was tinted wrong twice, customer requesting service credit.",
        "Delivery arrived two days late and held up the job.",
    ],
    "Scrubbability": [
        "Film burnished and wore through when scrubbed lightly.",
        "Cleaning the wall removed the paint down to the primer.",
    ],
    "Settling": [
        "Hard settled pigment in the bottom of the can, would not stir back in.",
        "Heavy settling after sitting on the shelf for {months} months.",
    ],
    "Skinning": [
        "Thick skin across the top of the product in a sealed can.",
        "Had to strain out skins before the product could be used.",
    ],
}
