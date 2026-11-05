"""The top-level field wiring shared by the two units worked examples."""


def wire_field_to_motor(d, field, *, fld, grp, motor_tag):
    """Wire `field[0]` to a top-level motor across the cabinet's own unit boundary, by a top-level cable."""
    motor = d.item("DEMO-MOTOR-4KW", tag=motor_tag, at=fld, group=grp)
    cable = d.cable("DEMO-CBL-4G1.5", tag=f"W{motor_tag}", length_mm=15000)
    cable.core(1, field[0].outer, motor["U"])
    return motor


def wire_field_to_switch(d, terminal, switch_port, *, cable_tag):
    """Wire one field terminal to one port of the shared top-level switch by its own one-core cable."""
    cable = d.cable("DEMO-CBL-4G1.5", tag=cable_tag, length_mm=15000)
    cable.core(1, terminal.outer, switch_port)
