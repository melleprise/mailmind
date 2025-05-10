import React, { ReactNode } from 'react';
import PropTypes from 'prop-types';
import { Box, Container, styled } from '@mui/material';

interface PageTitleWrapperProps {
  children: ReactNode;
}

const PageTitle = styled(Box)(
  ({ theme }) => `
    padding: ${theme.spacing(4)} 0;
  `
);

const PageTitleWrapper: React.FC<PageTitleWrapperProps> = ({ children }) => {
  return (
    <PageTitle className="MuiPageTitle-wrapper">
      <Container maxWidth="lg">{children}</Container>
    </PageTitle>
  );
};

PageTitleWrapper.propTypes = {
  children: PropTypes.node.isRequired
};

export default PageTitleWrapper; 