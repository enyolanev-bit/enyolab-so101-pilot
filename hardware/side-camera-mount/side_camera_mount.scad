// Boris — support caméra latérale (InnoMaker U20CAM-720P, carte ~32x32 mm)
//
// v1 : une seule pièce, angle de plongée fixé à l'impression (imprimer 2-3 angles).
// v2 : deux pièces, berceau qui pivote sur 2 vis M3 latérales (réglage à la main,
//      serrage par friction).
//
// Principe commun : la carte caméra glisse par le haut dans deux rails rainurés
// (aucune vis dans la carte, aucun trou de fixation à connaître). Le câble est
// bridé au socle par un collier passé dans deux fentes, pour qu'il ne tire pas
// sur la carte.
//
// Repère : X = largeur, Y = axe de visée (objectif vers +Y), Z = hauteur.
// Export : openscad -D 'part="v1"' -D tilt=10 -o v1.stl side_camera_mount.scad

/* [Sélection] */
part = "v1";          // "v1" | "v2_base" | "v2_cradle" | "v2_assembly"
tilt = 10;            // v1 : plongée de l'objectif vers le bas, en degrés (0 = horizontal)

/* [Caméra — À MESURER] */
pcb_w = 32.0;         // largeur carte (X)          — fiche revendeur : 32x32, ASSUMED
pcb_h = 32.0;         // hauteur carte (Z)
pcb_t = 1.6;          // épaisseur carte            — standard, ASSUMED
lens_off_z = 0;       // décalage vertical objectif / centre carte (+ = vers le haut)

/* [Position] */
lens_z_v1 = 22;       // hauteur du centre optique au-dessus de la table (v1)
lens_z_v2 = 24;       // idem v2 (un peu plus haut pour laisser pivoter le berceau)

/* [Rails] */
slot_clear  = 0.4;    // jeu sur l'épaisseur de carte (0.3 = serré, 0.6 = libre)
side_clear  = 0.3;    // jeu latéral par côté
groove_d    = 2.5;    // la carte entre de 2.5 mm dans chaque rail (côté objectif)
back_cover  = 1.2;    // la lèvre arrière ne recouvre que 1.2 mm (dégage le connecteur)
lip         = 2.5;    // épaisseur des lèvres avant/arrière (Y)
floor_t     = 2.0;    // épaisseur sous la carte
rail_h      = 28;     // hauteur des rails (au-dessus du bord bas de la carte)
bottom_lip  = 4;      // hauteur de la lèvre basse avant (ne doit pas masquer l'objectif)

/* [Socle] */
base_w  = 54;
base_d  = 42;
base_t  = 4;
tie_w   = 4.5;        // fente collier (largeur)
tie_l   = 3;          // fente collier (épaisseur)

/* [v2 pivot] */
side_wall_v2 = 7;     // épaisseur des rails v2 (logent la vis M3)
m3_pilot = 2.7;       // trou pilote auto-taraudage M3 dans le berceau
m3_clear = 3.4;       // trou de passage M3 dans les oreilles
ear_t    = 4;
ear_gap  = 0.4;       // jeu oreille / berceau par côté

$fn = 40;
eps = 0.01;

slot_w = pcb_t + slot_clear;
side_wall_v1 = 4;

// ---------------------------------------------------------------------------
// Berceau, repère local : carte entre y=0 et y=slot_w, bord bas à z=0, centrée en X.
module cradle(side_wall, pedestal = 0) {
    half_in = pcb_w / 2 + side_clear;          // fond de rainure
    half_out = half_in + side_wall;
    difference() {
        union() {
            // rails
            for (s = [-1, 1])
                translate([s > 0 ? pcb_w / 2 - groove_d : -half_out, -lip, -floor_t - pedestal])
                    cube([half_out - (pcb_w / 2 - groove_d), slot_w + 2 * lip, rail_h + floor_t + pedestal]);
            // traverse basse
            translate([-half_out, -lip, -floor_t - pedestal])
                cube([2 * half_out, slot_w + 2 * lip, floor_t + pedestal + bottom_lip]);
        }
        // rainure de la carte
        translate([-half_in, 0, 0]) cube([2 * half_in, slot_w, rail_h + 1]);
        // la lèvre arrière ne recouvre que back_cover mm de chaque bord
        translate([-(pcb_w / 2 - back_cover), -lip - eps, 0])
            cube([pcb_w - 2 * back_cover, lip + 2 * eps, rail_h + 1]);
        // fenêtre avant entre les rails, au-dessus de la lèvre basse
        translate([-(pcb_w / 2 - groove_d), slot_w - eps, bottom_lip])
            cube([pcb_w - 2 * groove_d, lip + 2 * eps, rail_h]);
    }
}

// fentes pour collier de serrage (bridage du câble), derrière le berceau
module tie_slots(y) {
    for (s = [-1, 1])
        translate([s * 6 - tie_w / 2, y - tie_l / 2, -1]) cube([tie_w, tie_l, base_t + 2]);
}

module base_plate(y_front) {
    translate([-base_w / 2, y_front - base_d, 0])
        cube([base_w, base_d, base_t]);
}

// ---------------------------------------------------------------------------
// v1 : monobloc à angle fixe
module v1() {
    lz = lens_z_v1;
    y_front = slot_w + lip;                    // socle affleurant l'avant du berceau
    pz = pcb_h / 2 + lens_off_z;               // hauteur de l'objectif dans le berceau
    difference() {
        union() {
            base_plate(y_front);
            intersection() {
                // pivot autour du centre optique : lens_z reste exact quel que soit tilt
                translate([0, slot_w / 2, lz])
                    rotate([-tilt, 0, 0])
                        translate([0, -slot_w / 2, -pz])
                            cradle(side_wall_v1, pedestal = 40);
                translate([-100, -100, 0]) cube([200, 200, 200]);
            }
        }
        tie_slots(y_front - base_d + 8);
    }
}

// ---------------------------------------------------------------------------
// v2 : berceau pivotant (imprimé debout, traverse sur le plateau)
module v2_cradle() {
    pz = pcb_h / 2 + lens_off_z;
    half_out = pcb_w / 2 + side_clear + side_wall_v2;
    difference() {
        translate([0, 0, floor_t]) cradle(side_wall_v2);
        // trous pilotes M3 sur l'axe du centre optique
        for (s = [-1, 1])
            translate([s * (half_out + eps), slot_w / 2, floor_t + pz])
                rotate([0, s * -90, 0]) cylinder(d = m3_pilot, h = side_wall_v2 - 1);
    }
}

module v2_base() {
    lz = lens_z_v2;
    half_out = pcb_w / 2 + side_clear + side_wall_v2;
    ear_x = half_out + ear_gap;
    ear_d = 14;
    y_front = slot_w / 2 + ear_d / 2;
    difference() {
        union() {
            base_plate(y_front);
            for (s = [-1, 1])
                translate([s > 0 ? ear_x : -ear_x - ear_t, slot_w / 2, 0])
                    hull() {
                        translate([0, -ear_d / 2, 0]) cube([ear_t, ear_d, base_t]);
                        translate([0, 0, lz]) rotate([0, 90, 0]) cylinder(d = ear_d, h = ear_t);
                    }
        }
        for (s = [-1, 1])
            translate([s > 0 ? ear_x - 1 : -ear_x - ear_t - 1, slot_w / 2, lz])
                rotate([0, 90, 0]) cylinder(d = m3_clear, h = ear_t + 2);
        tie_slots(y_front - base_d + 8);
    }
}

module v2_assembly() {
    pz = pcb_h / 2 + lens_off_z;
    v2_base();
    color("orange")
        translate([0, slot_w / 2, lens_z_v2])
            rotate([-tilt, 0, 0])
                translate([0, -slot_w / 2, -pz - floor_t]) v2_cradle();
    // carte fantôme, pour vérification visuelle
    %translate([0, slot_w / 2, lens_z_v2]) rotate([-tilt, 0, 0])
        translate([-pcb_w / 2, -pcb_t / 2, -pz]) cube([pcb_w, pcb_t, pcb_h]);
}

if (part == "v1") v1();
else if (part == "v2_base") v2_base();
else if (part == "v2_cradle") v2_cradle();
else if (part == "v2_assembly") v2_assembly();
