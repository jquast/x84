def main():
  from math import cos, sin, pi
  #blocks = fromCP437(''.join(chr(176),chr(166),chr(178),chr(220),chr(223))
  blocks = ".,-~:;=!*#$@"
  term = getterminal()
  # www.a1k0n.net/2011/07/20/donut-math.html
  theta_spacing = 0.07
  phi_spacing   = 0.02
  R1 = 1.0
  R2 = 2.0
  K2 = 5.0
  #  Calculate K1 based on screen size: the maximum x-distance occurs roughly at
  #  the edge of the torus, which is at x=R1+R2, z=0.  we want that to be
  #  displaced 3/8ths of the width of the screen, which is 3/4th of the way from
  #  the center to the side of the screen.
  #  screen_width*3/8 = K1*(R1+R2)/(K2+0)
  #  screen_width*K2*3/(8*(R1+R2)) = K1
  K1 = float(term.columns/5)*K2*3/(8*(R1+R2))

  def render_frame(A, B):
    lxp, lyp, lc = 1, 1, ''
    #  precompute sines and cosines of A and B
    cosA, sinA = cos(A), sin(A);
    cosB, sinB = cos(B), sin(B);
    output = list([list([' ' for n in range(term.columns)]) \
      for n in range(term.rows)])
    zbuffer = list([list([0 for n in range(term.columns)]) \
      for n in range(term.rows)])

    # theta goes around the cross-sectional circle of a torus
    theta = 0.0
    while theta < 2*pi:
      # precompute sines and cosines of theta
      costheta, sintheta = cos(theta), sin(theta);
      # phi goes around the center of revolution of a torus
      phi = 0.0
      while phi < 2*pi:
        # precompute sines and cosines of phi
        cosphi, sinphi = cos(phi), sin(phi)
        # the x,y coordinate of the circle, before revolving (factored out
        # of the above equations)
        circlex = R2 + R1*costheta
        circley = R1*sintheta

        # final 3D (x,y,z) coordinate after rotations,
        # directly from our math above
        x = circlex*(cosB*cosphi + sinA*sinB*sinphi) - circley*cosA*sinB
        y = circlex*(sinB*cosphi - sinA*cosB*sinphi) + circley*cosA*cosB
        z = K2 + cosA*circlex*sinphi + circley*sinA;
        ooz = 1.0/z;  # "one over z"
        # x and y projection. note that y is negated here,
        # because y goes up in 3D space but down on 2D displays.
        xp = int((float(term.columns)/2 + K1*ooz*x))
        yp = int((float(term.rows)/2 - K1*ooz*y))

        # calculate luminance.  ugly, but correct.
        L = cosphi*costheta*sinB - cosA*costheta*sinphi - sinA*sintheta + \
            cosB*(cosA*sintheta - costheta*sinA*sinphi)
        # L ranges from -sqrt(2) to +sqrt(2).  If it's < 0, the surface is
        # pointing away from us, so we won't bother trying to plot it.
        if (L>0):
          # test against the z-buffer.  larger 1/z means the pixel is closer to
          # the viewer than what's already plotted.
          if xp < term.columns-2 and xp > 0 and yp < term.rows-2 and yp > 0 \
              and (ooz > zbuffer[yp][xp]):
            zbuffer[yp][xp] = ooz
            # this brings L into the range 0..11 (8*sqrt(2) = 11.3)
            luminance_index = int(L*8)
            # now we lookup the character corresponding to the
            # luminance and plot it in our output:
            output[yp][xp] = blocks[luminance_index]
        phi += phi_spacing
      theta += theta_spacing
    return output

  A, B = 1.0, 1.0
  echo (term.clear)
  maxtop = -1
  maxleft = -1
  echo (term.hide_cursor)
  while True:
    output = render_frame (A, B)
    top = -1
    echo (term.move(0, 0))
    echo ((term.clear_eol+'\r\n').join([''.join(l).rstrip() for l in output]))
    ch = getch(0.01)
    if ch == 'q':
      break
    A += 0.09
    B += 0.05
  echo (term.show_cursor)
