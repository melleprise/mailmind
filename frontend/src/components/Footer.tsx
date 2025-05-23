import React from 'react';
import { Box, Container, Link, Typography, styled } from '@mui/material';

const FooterWrapper = styled(Box)(
  ({ theme }) => `
        border-radius: 0;
        margin: ${theme.spacing(3)} 0;
`
);

function Footer() {
  return (
    <FooterWrapper className="footer-wrapper">
      <Container maxWidth="lg">
        <Box
          py={3}
          display={{ xs: 'block', md: 'flex' }}
          alignItems="center"
          textAlign={{ xs: 'center', md: 'left' }}
          justifyContent="space-between"
        >
          <Box>
            <Typography variant="subtitle1">
              &copy; {new Date().getFullYear()} - MailMind AI
            </Typography>
          </Box>
          <Typography sx={{ pt: { xs: 2, md: 0 } }} variant="subtitle1">
            Crafted by{' '}
            <Link
              href="https://yourcompany.com" // Replace with actual link if needed
              target="_blank"
              rel="noopener noreferrer"
            >
              YourCompany
            </Link>
          </Typography>
        </Box>
      </Container>
    </FooterWrapper>
  );
}

export default Footer; 