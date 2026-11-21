"""Stock LTZ CSM payload hashes derived from a successful historical transfer.

Hashes cover unwrapped CSM containers, not outer gzip cache files. They verify
only byte identity to that historical transaction, not present compatibility.
"""
from .calibration_transaction import TrustedContainer

LTZ_REFERENCE = (
    TrustedContainer(2, "87863250", "604f34c19822f204a852a252b601fb1d9b3dc425a989a9a41a807864a509b286"),
    TrustedContainer(3, "84517309", "79167d182ca5cde22b8e8da80e61f2058f3d20d5dd595158970cdea914118f4d"),
    TrustedContainer(4, "85045371", "27aa0cb3427225518e51cd1a5c53d6139462609ea11df106bf27bde2a7136231"),
    TrustedContainer(5, "87846416", "7d58ff19805c296463fcd6764a1b9cb08028f905c91a2d5d89b4fc7f114dbb5e"),
    TrustedContainer(6, "87846371", "d34e1deaaf748e8c27b6d9980856e2236d4614223686288f4ebd340b2bbbacf7"),
    TrustedContainer(7, "85783460", "37756273d117233e0ccd503606bbdefe3524a7b55cc1834c34d93eaf5e565ace"),
    TrustedContainer(8, "87846432", "c97114731de14bc5f748f98ed10f931fb5e0a432b40bb1e75c01efd43b7055b4"),
    TrustedContainer(9, "87846376", "1af636050a32ae729a7a21a29212943ff98fc2ea8798823f9c8f285772a97e2c"),
    TrustedContainer(10, "87846368", "0c5f7a1aa31b1c6551a34b04df32368f2913a02d3d4dcc798fbb345511038cb0"),
    TrustedContainer(11, "86292118", "0dfe3c339a14811d8a2ac6aeebfae04f5f27ae720d60fca7cb60096a5c22b789"),
    TrustedContainer(12, "85102312", "c8c36547fa2292b5aed6bb58b063e34da8b4490c60747dee5c40e50f6edf532e"),
    TrustedContainer(13, "87846384", "3af4aa72d303dff844659ccb90d7d1514436c47412b7f8e0162a75a9d7198b1e"),
    TrustedContainer(14, "84517418", "a07d08ead8cb96147cf2a8ff31788b0e22e76e961ffce0516918e37f26a824cf"),
    TrustedContainer(15, "87846380", "2e6f8247aecfdfc32997fbd3779c1917c7360579484de39b21f757d1d2740f53"),
)
